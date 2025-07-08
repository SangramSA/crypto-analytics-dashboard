#!/usr/bin/env python3
"""
Crypto Analytics Dashboard - Lambda Stream Processor

This Lambda function processes real-time cryptocurrency market data from Kinesis
Data Streams. It validates data quality, enriches records with calculated fields,
and writes to S3 in partitioned format.

Author: Crypto Analytics Team
Version: 1.0.0
"""

import base64
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import boto3
import structlog
from botocore.exceptions import ClientError

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize AWS clients
s3_client = boto3.client('s3')
cloudwatch = boto3.client('cloudwatch')
sns_client = boto3.client('sns')


class DataQualityValidator:
    """Validates incoming market data for quality and completeness."""
    
    def __init__(self):
        """Initialize validator with configuration."""
        self.min_price = float(os.getenv("PRICE_VALIDATION_MIN", "0.01"))
        self.max_price = float(os.getenv("PRICE_VALIDATION_MAX", "1000000.0"))
        self.min_volume = float(os.getenv("VOLUME_VALIDATION_MIN", "0.0"))
        self.timestamp_tolerance = int(os.getenv("TIMESTAMP_TOLERANCE_SECONDS", "300"))
        self.quality_threshold = float(os.getenv("DATA_QUALITY_THRESHOLD", "0.8"))
    
    def validate_record(self, record: Dict) -> Tuple[bool, float, List[str]]:
        """Validate a market data record.
        
        Args:
            record: Market data record to validate
            
        Returns:
            Tuple of (is_valid, quality_score, error_messages)
        """
        errors = []
        score = 1.0
        
        # Check required fields
        required_fields = ['exchange', 'symbol', 'timestamp', 'price', 'volume']
        for field in required_fields:
            if field not in record:
                errors.append(f"Missing required field: {field}")
                score -= 0.2
        
        # Validate price
        if 'price' in record:
            try:
                price = float(record['price'])
                if not (self.min_price <= price <= self.max_price):
                    errors.append(f"Price {price} outside valid range [{self.min_price}, {self.max_price}]")
                    score -= 0.3
            except (ValueError, TypeError):
                errors.append("Invalid price format")
                score -= 0.3
        
        # Validate volume
        if 'volume' in record:
            try:
                volume = float(record['volume'])
                if volume < self.min_volume:
                    errors.append(f"Volume {volume} below minimum {self.min_volume}")
                    score -= 0.2
            except (ValueError, TypeError):
                errors.append("Invalid volume format")
                score -= 0.2
        
        # Validate timestamp
        if 'timestamp' in record:
            try:
                timestamp = int(record['timestamp'])
                current_time = int(time.time() * 1000)  # Convert to milliseconds
                if abs(current_time - timestamp) > (self.timestamp_tolerance * 1000):
                    errors.append(f"Timestamp {timestamp} too old")
                    score -= 0.1
            except (ValueError, TypeError):
                errors.append("Invalid timestamp format")
                score -= 0.1
        
        # Validate exchange
        valid_exchanges = ['binance', 'coinbase', 'kraken']
        if 'exchange' in record and record['exchange'].lower() not in valid_exchanges:
            errors.append(f"Invalid exchange: {record['exchange']}")
            score -= 0.2
        
        return score >= self.quality_threshold, max(0.0, score), errors


class DataEnricher:
    """Enriches market data with calculated fields and technical indicators."""
    
    def __init__(self):
        """Initialize enricher."""
        self.price_history: Dict[str, List[float]] = {}
        self.max_history_size = 100
    
    def enrich_record(self, record: Dict) -> Dict:
        """Enrich a market data record with calculated fields.
        
        Args:
            record: Market data record to enrich
            
        Returns:
            Enriched record
        """
        enriched = record.copy()
        
        # Add processing timestamp
        enriched['processed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Calculate spread if bid/ask available
        if 'bid' in record and 'ask' in record:
            try:
                bid = float(record['bid'])
                ask = float(record['ask'])
                if bid > 0 and ask > 0:
                    enriched['spread'] = ask - bid
                    enriched['spread_percentage'] = ((ask - bid) / bid) * 100
            except (ValueError, TypeError):
                pass
        
        # Calculate price change
        symbol = record.get('symbol', 'unknown')
        price = float(record.get('price', 0))
        
        if symbol in self.price_history and self.price_history[symbol]:
            previous_price = self.price_history[symbol][-1]
            if previous_price > 0:
                enriched['price_change'] = price - previous_price
                enriched['price_change_percentage'] = ((price - previous_price) / previous_price) * 100
        
        # Update price history
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(price)
        if len(self.price_history[symbol]) > self.max_history_size:
            self.price_history[symbol].pop(0)
        
        # Calculate simple moving average
        if len(self.price_history[symbol]) >= 5:
            sma_5 = sum(self.price_history[symbol][-5:]) / 5
            enriched['sma_5'] = sma_5
        
        if len(self.price_history[symbol]) >= 10:
            sma_10 = sum(self.price_history[symbol][-10:]) / 10
            enriched['sma_10'] = sma_10
        
        # Calculate volatility
        if len(self.price_history[symbol]) >= 10:
            prices = self.price_history[symbol][-10:]
            mean_price = sum(prices) / len(prices)
            variance = sum((p - mean_price) ** 2 for p in prices) / len(prices)
            enriched['volatility'] = variance ** 0.5
        
        return enriched


class S3Writer:
    """Handles writing data to S3 in partitioned format."""
    
    def __init__(self):
        """Initialize S3 writer."""
        self.bucket_name = os.getenv("S3_BUCKET_NAME", "crypto-analytics-data")
        self.raw_prefix = os.getenv("S3_RAW_DATA_PREFIX", "raw/")
        self.batch_size = int(os.getenv("S3_BATCH_SIZE", "100"))
        self.records_buffer: List[Dict] = []
    
    def add_record(self, record: Dict) -> None:
        """Add a record to the buffer.
        
        Args:
            record: Record to add
        """
        self.records_buffer.append(record)
        
        if len(self.records_buffer) >= self.batch_size:
            self._flush_buffer()
    
    def _flush_buffer(self) -> None:
        """Flush the buffer to S3."""
        if not self.records_buffer:
            return
        
        try:
            # Group records by partition
            partitions: Dict[str, List[Dict]] = {}
            
            for record in self.records_buffer:
                partition_key = self._get_partition_key(record)
                if partition_key not in partitions:
                    partitions[partition_key] = []
                partitions[partition_key].append(record)
            
            # Write each partition
            for partition_key, records in partitions.items():
                self._write_partition(partition_key, records)
            
            self.records_buffer.clear()
            
        except Exception as e:
            logger.error("Failed to flush buffer to S3", error=str(e))
            # In production, you might want to send to DLQ here
    
    def _get_partition_key(self, record: Dict) -> str:
        """Generate partition key for S3.
        
        Args:
            record: Market data record
            
        Returns:
            Partition key string
        """
        exchange = record.get('exchange', 'unknown')
        symbol = record.get('symbol', 'unknown')
        
        # Parse timestamp
        try:
            timestamp = int(record.get('timestamp', 0))
            dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        except (ValueError, TypeError):
            dt = datetime.now(timezone.utc)
        
        year = dt.year
        month = dt.month
        day = dt.day
        hour = dt.hour
        
        return f"{exchange}/{symbol}/year={year}/month={month:02d}/day={day:02d}/hour={hour:02d}"
    
    def _write_partition(self, partition_key: str, records: List[Dict]) -> None:
        """Write records to a specific partition.
        
        Args:
            partition_key: S3 partition key
            records: Records to write
        """
        try:
            # Create file key
            timestamp = int(time.time())
            file_key = f"{self.raw_prefix}{partition_key}/data_{timestamp}.json"
            
            # Prepare data
            data = {
                'records': records,
                'count': len(records),
                'timestamp': timestamp,
                'partition': partition_key
            }
            
            # Upload to S3
            s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=json.dumps(data, separators=(',', ':')),
                ContentType='application/json'
            )
            
            logger.info(
                "Successfully wrote partition to S3",
                partition=partition_key,
                records_count=len(records),
                file_key=file_key
            )
            
        except ClientError as e:
            logger.error(
                "Failed to write partition to S3",
                partition=partition_key,
                error=str(e)
            )
            raise
    
    def flush(self) -> None:
        """Flush any remaining records."""
        self._flush_buffer()


class CloudWatchMetrics:
    """Handles publishing metrics to CloudWatch."""
    
    def __init__(self):
        """Initialize CloudWatch metrics."""
        self.namespace = os.getenv("CLOUDWATCH_METRIC_NAMESPACE", "CryptoAnalytics")
        self.metrics_buffer: List[Dict] = []
        self.max_buffer_size = 20
    
    def record_metric(self, metric_name: str, value: float, unit: str = "Count", 
                     dimensions: Optional[List[Dict]] = None) -> None:
        """Record a metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Metric unit
            dimensions: Metric dimensions
        """
        metric = {
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit,
            'Timestamp': datetime.now(timezone.utc)
        }
        
        if dimensions:
            metric['Dimensions'] = dimensions
        
        self.metrics_buffer.append(metric)
        
        if len(self.metrics_buffer) >= self.max_buffer_size:
            self._publish_metrics()
    
    def _publish_metrics(self) -> None:
        """Publish buffered metrics to CloudWatch."""
        if not self.metrics_buffer:
            return
        
        try:
            cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=self.metrics_buffer
            )
            
            self.metrics_buffer.clear()
            
        except ClientError as e:
            logger.error("Failed to publish metrics to CloudWatch", error=str(e))
    
    def flush(self) -> None:
        """Flush any remaining metrics."""
        self._publish_metrics()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda function handler for processing Kinesis records.
    
    Args:
        event: Lambda event containing Kinesis records
        context: Lambda context
        
    Returns:
        Response with batch item failures
    """
    start_time = time.time()
    
    # Initialize components
    validator = DataQualityValidator()
    enricher = DataEnricher()
    s3_writer = S3Writer()
    metrics = CloudWatchMetrics()
    
    # Statistics
    total_records = 0
    valid_records = 0
    invalid_records = 0
    failed_records = []
    
    try:
        # Process each Kinesis record
        for record in event['Records']:
            total_records += 1
            
            try:
                # Decode Kinesis record
                payload = base64.b64decode(record['kinesis']['data']).decode('utf-8')
                market_data = json.loads(payload)
                
                # Validate record
                is_valid, quality_score, errors = validator.validate_record(market_data)
                
                if is_valid:
                    # Enrich record
                    enriched_data = enricher.enrich_record(market_data)
                    enriched_data['quality_score'] = quality_score
                    
                    # Write to S3
                    s3_writer.add_record(enriched_data)
                    
                    valid_records += 1
                    
                    # Record metrics
                    metrics.record_metric(
                        'RecordsProcessed',
                        1,
                        dimensions=[{'Name': 'Exchange', 'Value': market_data.get('exchange', 'unknown')}]
                    )
                    
                    metrics.record_metric(
                        'DataQualityScore',
                        quality_score,
                        unit='None',
                        dimensions=[{'Name': 'Exchange', 'Value': market_data.get('exchange', 'unknown')}]
                    )
                    
                else:
                    invalid_records += 1
                    logger.warning(
                        "Invalid record detected",
                        errors=errors,
                        quality_score=quality_score,
                        record=market_data
                    )
                    
                    # Record invalid record metric
                    metrics.record_metric('InvalidRecords', 1)
                    
                    # Send to DLQ if configured
                    if os.getenv("DLQ_ENABLED", "false").lower() == "true":
                        failed_records.append({
                            'recordId': record['recordId'],
                            'reason': f"Data quality validation failed: {errors}"
                        })
                
            except Exception as e:
                invalid_records += 1
                logger.error(
                    "Failed to process record",
                    record_id=record['recordId'],
                    error=str(e)
                )
                
                failed_records.append({
                    'recordId': record['recordId'],
                    'reason': f"Processing error: {str(e)}"
                })
        
        # Flush remaining data
        s3_writer.flush()
        metrics.flush()
        
        # Record final metrics
        processing_time = time.time() - start_time
        metrics.record_metric('ProcessingTime', processing_time, unit='Seconds')
        metrics.record_metric('TotalRecords', total_records)
        metrics.record_metric('ValidRecords', valid_records)
        metrics.record_metric('InvalidRecords', invalid_records)
        
        # Log summary
        logger.info(
            "Lambda processing completed",
            total_records=total_records,
            valid_records=valid_records,
            invalid_records=invalid_records,
            processing_time=processing_time,
            memory_used=context.memory_limit_in_mb if hasattr(context, 'memory_limit_in_mb') else 'unknown'
        )
        
        # Send alert if error rate is high
        if total_records > 0 and (invalid_records / total_records) > 0.1:
            _send_alert(f"High error rate detected: {invalid_records}/{total_records} records failed")
        
        return {
            'batchItemFailures': failed_records
        }
        
    except Exception as e:
        logger.error("Lambda function failed", error=str(e))
        _send_alert(f"Lambda function failed: {str(e)}")
        raise


def _send_alert(message: str) -> None:
    """Send alert via SNS.
    
    Args:
        message: Alert message
    """
    try:
        sns_topic_arn = os.getenv("SNS_TOPIC_ARN")
        if sns_topic_arn:
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Message=message,
                Subject="Crypto Analytics Alert"
            )
    except Exception as e:
        logger.error("Failed to send alert", error=str(e)) 