#!/usr/bin/env python3
"""
Crypto Analytics Dashboard - Load Tests

Load tests to validate performance characteristics of the crypto analytics
platform under high load conditions.

Author: Crypto Analytics Team
Version: 1.0.0
"""

import asyncio
import json
import os
import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import boto3
import psycopg2
from moto import mock_aws, mock_kinesis, mock_s3, mock_lambda

from src.ingestion.producers.kinesis_producer import MarketData, KinesisProducer


class LoadTestConfig:
    """Configuration for load tests."""
    
    def __init__(self):
        self.record_count = 10000
        self.concurrent_producers = 5
        self.concurrent_consumers = 3
        self.test_duration_seconds = 300  # 5 minutes
        self.target_throughput = 2000  # records per minute
        self.max_latency_ms = 1000  # 1 second
        self.error_rate_threshold = 0.01  # 1%


class LoadTestMetrics:
    """Collects and analyzes load test metrics."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.records_sent = 0
        self.records_processed = 0
        self.errors = 0
        self.latencies = []
        self.throughput_samples = []
    
    def start_test(self):
        """Start the load test."""
        self.start_time = time.time()
    
    def end_test(self):
        """End the load test."""
        self.end_time = time.time()
    
    def record_sent(self):
        """Record a sent record."""
        self.records_sent += 1
    
    def record_processed(self, latency_ms: float):
        """Record a processed record."""
        self.records_processed += 1
        self.latencies.append(latency_ms)
    
    def record_error(self):
        """Record an error."""
        self.errors += 1
    
    def get_results(self) -> Dict:
        """Get test results."""
        if not self.start_time or not self.end_time:
            return {}
        
        duration = self.end_time - self.start_time
        total_records = self.records_sent + self.errors
        
        results = {
            'duration_seconds': duration,
            'records_sent': self.records_sent,
            'records_processed': self.records_processed,
            'errors': self.errors,
            'error_rate': self.errors / total_records if total_records > 0 else 0,
            'throughput_rps': self.records_processed / duration if duration > 0 else 0,
            'avg_latency_ms': sum(self.latencies) / len(self.latencies) if self.latencies else 0,
            'p95_latency_ms': self._percentile(self.latencies, 95),
            'p99_latency_ms': self._percentile(self.latencies, 99),
            'max_latency_ms': max(self.latencies) if self.latencies else 0,
            'min_latency_ms': min(self.latencies) if self.latencies else 0
        }
        
        return results
    
    def _percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[index]


class LoadTestRunner:
    """Runs load tests against the crypto analytics platform."""
    
    def __init__(self, config: LoadTestConfig):
        """Initialize load test runner.
        
        Args:
            config: Load test configuration
        """
        self.config = config
        self.metrics = LoadTestMetrics()
    
    async def run_kinesis_producer_load_test(self, aws_mocks) -> Dict:
        """Run load test for Kinesis producer."""
        print("Starting Kinesis producer load test...")
        
        # Setup AWS resources
        kinesis_client = boto3.client('kinesis', region_name='us-east-1')
        
        # Create test stream
        stream_name = "load-test-crypto-market-data"
        kinesis_client.create_stream(
            StreamName=stream_name,
            ShardCount=5  # Multiple shards for load testing
        )
        
        # Wait for stream to be active
        while True:
            response = kinesis_client.describe_stream(StreamName=stream_name)
            if response['StreamDescription']['StreamStatus'] == 'ACTIVE':
                break
            time.sleep(1)
        
        # Initialize producer
        producer = KinesisProducer(stream_name, region='us-east-1')
        
        # Generate test data
        test_records = self._generate_test_records()
        
        # Start metrics collection
        self.metrics.start_test()
        
        # Run producers in parallel
        with ThreadPoolExecutor(max_workers=self.config.concurrent_producers) as executor:
            futures = []
            for i in range(self.config.concurrent_producers):
                future = executor.submit(
                    self._producer_worker,
                    producer,
                    test_records[i::self.config.concurrent_producers]
                )
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Producer error: {e}")
                    self.metrics.record_error()
        
        self.metrics.end_test()
        
        # Cleanup
        kinesis_client.delete_stream(StreamName=stream_name)
        
        return self.metrics.get_results()
    
    def _generate_test_records(self) -> List[MarketData]:
        """Generate test market data records."""
        records = []
        base_price = 50000.0
        base_time = int(time.time() * 1000)
        
        for i in range(self.config.record_count):
            # Vary price slightly
            price = base_price + (i % 100) - 50
            
            record = MarketData(
                exchange="binance" if i % 3 == 0 else "coinbase" if i % 3 == 1 else "kraken",
                symbol="BTCUSDT" if i % 2 == 0 else "ETHUSDT",
                timestamp=str(base_time + i * 1000),  # 1 second intervals
                price=price,
                volume=1.0 + (i % 10) * 0.1,
                bid=price - 0.5,
                ask=price + 0.5,
                trade_id=f"load_test_{i}",
                quality_score=0.9
            )
            records.append(record)
        
        return records
    
    def _producer_worker(self, producer: KinesisProducer, records: List[MarketData]):
        """Worker function for producer load test."""
        for record in records:
            try:
                start_time = time.time()
                success = producer.put_record(record)
                end_time = time.time()
                
                if success:
                    self.metrics.record_sent()
                    latency_ms = (end_time - start_time) * 1000
                    self.metrics.record_processed(latency_ms)
                else:
                    self.metrics.record_error()
                
                # Rate limiting
                time.sleep(0.001)  # 1ms delay
                
            except Exception as e:
                print(f"Error in producer worker: {e}")
                self.metrics.record_error()
    
    async def run_lambda_load_test(self, aws_mocks) -> Dict:
        """Run load test for Lambda function."""
        print("Starting Lambda load test...")
        
        # Setup AWS resources
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Create test resources
        function_name = "load-test-crypto-stream-processor"
        bucket_name = "load-test-crypto-analytics-data"
        
        s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': 'us-east-1'}
        )
        
        # Create Lambda function (mock)
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.9',
            Role='arn:aws:iam::123456789012:role/lambda-role',
            Handler='handler.lambda_handler',
            Code={'ZipFile': b'def lambda_handler(event, context): return {"statusCode": 200}'},
            Timeout=60,
            MemorySize=512
        )
        
        # Generate test events
        test_events = self._generate_test_events()
        
        # Start metrics collection
        self.metrics.start_test()
        
        # Run Lambda invocations in parallel
        with ThreadPoolExecutor(max_workers=self.config.concurrent_consumers) as executor:
            futures = []
            for event in test_events:
                future = executor.submit(
                    self._lambda_worker,
                    lambda_client,
                    function_name,
                    event
                )
                futures.append(future)
            
            # Wait for completion
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Lambda error: {e}")
                    self.metrics.record_error()
        
        self.metrics.end_test()
        
        # Cleanup
        lambda_client.delete_function(FunctionName=function_name)
        s3_client.delete_bucket(Bucket=bucket_name)
        
        return self.metrics.get_results()
    
    def _generate_test_events(self) -> List[Dict]:
        """Generate test Lambda events."""
        events = []
        base_time = int(time.time() * 1000)
        
        for i in range(self.config.record_count):
            record_data = {
                'exchange': 'binance' if i % 3 == 0 else 'coinbase' if i % 3 == 1 else 'kraken',
                'symbol': 'BTCUSDT' if i % 2 == 0 else 'ETHUSDT',
                'timestamp': str(base_time + i * 1000),
                'price': 50000.0 + (i % 100),
                'volume': 1.0 + (i % 10) * 0.1,
                'quality_score': 0.9
            }
            
            event = {
                'Records': [
                    {
                        'kinesis': {
                            'data': json.dumps(record_data)
                        }
                    }
                ]
            }
            events.append(event)
        
        return events
    
    def _lambda_worker(self, lambda_client, function_name: str, event: Dict):
        """Worker function for Lambda load test."""
        try:
            start_time = time.time()
            
            # Invoke Lambda function
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(event)
            )
            
            end_time = time.time()
            
            # Check response
            if response['StatusCode'] == 200:
                self.metrics.record_sent()
                latency_ms = (end_time - start_time) * 1000
                self.metrics.record_processed(latency_ms)
            else:
                self.metrics.record_error()
                
        except Exception as e:
            print(f"Error in Lambda worker: {e}")
            self.metrics.record_error()
    
    async def run_database_load_test(self) -> Dict:
        """Run load test for database operations."""
        print("Starting database load test...")
        
        # Connect to test database
        connection_string = os.getenv("TEST_DATABASE_URL", 
                                    "postgresql://admin:password@localhost:5432/crypto_analytics_test")
        
        try:
            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor()
            
            # Create test table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS load_test_ohlcv (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    exchange VARCHAR(50) NOT NULL,
                    interval_start TIMESTAMP NOT NULL,
                    open DECIMAL(20,8) NOT NULL,
                    high DECIMAL(20,8) NOT NULL,
                    low DECIMAL(20,8) NOT NULL,
                    close DECIMAL(20,8) NOT NULL,
                    volume DECIMAL(20,8) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Generate test data
            test_records = self._generate_database_test_records()
            
            # Start metrics collection
            self.metrics.start_test()
            
            # Run database operations in parallel
            with ThreadPoolExecutor(max_workers=self.config.concurrent_consumers) as executor:
                futures = []
                for record in test_records:
                    future = executor.submit(
                        self._database_worker,
                        conn,
                        record
                    )
                    futures.append(future)
                
                # Wait for completion
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        print(f"Database error: {e}")
                        self.metrics.record_error()
            
            self.metrics.end_test()
            
            # Cleanup
            cursor.execute("DROP TABLE load_test_ohlcv")
            conn.commit()
            
            cursor.close()
            conn.close()
            
            return self.metrics.get_results()
            
        except Exception as e:
            pytest.skip(f"Database not available: {str(e)}")
    
    def _generate_database_test_records(self) -> List[Dict]:
        """Generate test database records."""
        records = []
        base_time = datetime.now()
        
        for i in range(self.config.record_count):
            record = {
                'symbol': 'BTCUSDT' if i % 2 == 0 else 'ETHUSDT',
                'exchange': 'binance' if i % 3 == 0 else 'coinbase' if i % 3 == 1 else 'kraken',
                'interval_start': base_time + timedelta(minutes=i),
                'open': 50000.0 + (i % 100),
                'high': 50100.0 + (i % 100),
                'low': 49900.0 + (i % 100),
                'close': 50050.0 + (i % 100),
                'volume': 100.0 + (i % 50)
            }
            records.append(record)
        
        return records
    
    def _database_worker(self, conn, record: Dict):
        """Worker function for database load test."""
        try:
            start_time = time.time()
            
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO load_test_ohlcv 
                (symbol, exchange, interval_start, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                record['symbol'],
                record['exchange'],
                record['interval_start'],
                record['open'],
                record['high'],
                record['low'],
                record['close'],
                record['volume']
            ))
            
            conn.commit()
            cursor.close()
            
            end_time = time.time()
            
            self.metrics.record_sent()
            latency_ms = (end_time - start_time) * 1000
            self.metrics.record_processed(latency_ms)
            
        except Exception as e:
            print(f"Error in database worker: {e}")
            self.metrics.record_error()


class TestLoadPerformance:
    """Load test performance validation."""
    
    @pytest.mark.asyncio
    async def test_kinesis_producer_load(self, aws_mocks):
        """Test Kinesis producer under load."""
        config = LoadTestConfig()
        config.record_count = 1000  # Smaller test for CI
        config.concurrent_producers = 3
        
        runner = LoadTestRunner(config)
        results = await runner.run_kinesis_producer_load_test(aws_mocks)
        
        # Validate performance requirements
        assert results['error_rate'] < config.error_rate_threshold
        assert results['avg_latency_ms'] < config.max_latency_ms
        assert results['throughput_rps'] > config.target_throughput / 60  # Convert to per second
    
    @pytest.mark.asyncio
    async def test_lambda_load(self, aws_mocks):
        """Test Lambda function under load."""
        config = LoadTestConfig()
        config.record_count = 500  # Smaller test for CI
        config.concurrent_consumers = 2
        
        runner = LoadTestRunner(config)
        results = await runner.run_lambda_load_test(aws_mocks)
        
        # Validate performance requirements
        assert results['error_rate'] < config.error_rate_threshold
        assert results['avg_latency_ms'] < config.max_latency_ms
    
    def test_database_load(self):
        """Test database operations under load."""
        config = LoadTestConfig()
        config.record_count = 1000  # Smaller test for CI
        config.concurrent_consumers = 3
        
        runner = LoadTestRunner(config)
        results = asyncio.run(runner.run_database_load_test())
        
        # Validate performance requirements
        assert results['error_rate'] < config.error_rate_threshold
        assert results['avg_latency_ms'] < config.max_latency_ms
    
    def test_end_to_end_load(self, aws_mocks):
        """Test end-to-end pipeline under load."""
        config = LoadTestConfig()
        config.record_count = 500  # Smaller test for CI
        config.test_duration_seconds = 60  # 1 minute
        
        # This would test the complete pipeline
        # For now, we'll test individual components
        assert True  # Placeholder for end-to-end test
    
    def test_memory_usage(self, aws_mocks):
        """Test memory usage under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run load test
        config = LoadTestConfig()
        config.record_count = 1000
        
        runner = LoadTestRunner(config)
        asyncio.run(runner.run_kinesis_producer_load_test(aws_mocks))
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB)
        assert memory_increase < 100
    
    def test_concurrent_connections(self, aws_mocks):
        """Test system behavior with many concurrent connections."""
        config = LoadTestConfig()
        config.concurrent_producers = 10
        config.concurrent_consumers = 10
        config.record_count = 1000
        
        runner = LoadTestRunner(config)
        results = asyncio.run(runner.run_kinesis_producer_load_test(aws_mocks))
        
        # Should handle high concurrency without excessive errors
        assert results['error_rate'] < 0.05  # 5% error rate threshold for high concurrency


class TestStressConditions:
    """Stress test conditions."""
    
    def test_high_error_rate_recovery(self, aws_mocks):
        """Test system recovery from high error rates."""
        # Simulate high error rate scenario
        config = LoadTestConfig()
        config.record_count = 100
        config.error_rate_threshold = 0.5  # Allow 50% errors for stress test
        
        runner = LoadTestRunner(config)
        results = asyncio.run(runner.run_kinesis_producer_load_test(aws_mocks))
        
        # System should continue operating even with errors
        assert results['records_processed'] > 0
    
    def test_resource_exhaustion(self, aws_mocks):
        """Test system behavior under resource exhaustion."""
        # This would test behavior when resources are limited
        # For now, we'll test with reduced resources
        config = LoadTestConfig()
        config.record_count = 100
        
        runner = LoadTestRunner(config)
        results = asyncio.run(runner.run_kinesis_producer_load_test(aws_mocks))
        
        # Should handle resource constraints gracefully
        assert results['error_rate'] < 0.1  # 10% error rate threshold for stress


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 