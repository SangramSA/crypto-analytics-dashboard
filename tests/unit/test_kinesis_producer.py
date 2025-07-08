#!/usr/bin/env python3
"""
Unit tests for the Kinesis producer module.

This module contains comprehensive unit tests for the crypto analytics
Kinesis producer, including data validation, error handling, and
performance testing.
"""

import json
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ingestion.producers.kinesis_producer import (
    MarketData, KinesisProducer, BinanceConnector, 
    CoinbaseConnector, MarketDataStreamer
)


class TestMarketData(unittest.TestCase):
    """Test cases for MarketData class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_market_data = MarketData(
            exchange="binance",
            symbol="btcusdt",
            timestamp="1640995200000",
            price=50000.0,
            volume=1.5,
            bid=49999.0,
            ask=50001.0,
            trade_id="12345",
            quality_score=0.95
        )
    
    def test_market_data_creation(self):
        """Test MarketData object creation."""
        self.assertEqual(self.valid_market_data.exchange, "binance")
        self.assertEqual(self.valid_market_data.symbol, "btcusdt")
        self.assertEqual(self.valid_market_data.price, 50000.0)
        self.assertEqual(self.valid_market_data.volume, 1.5)
        self.assertEqual(self.valid_market_data.quality_score, 0.95)
    
    def test_market_data_to_dict(self):
        """Test conversion to dictionary."""
        data_dict = self.valid_market_data.to_dict()
        
        self.assertIsInstance(data_dict, dict)
        self.assertEqual(data_dict["exchange"], "binance")
        self.assertEqual(data_dict["symbol"], "btcusdt")
        self.assertEqual(data_dict["price"], 50000.0)
        self.assertEqual(data_dict["volume"], 1.5)
    
    def test_market_data_validation_valid(self):
        """Test validation with valid data."""
        self.assertTrue(self.valid_market_data.validate())
    
    def test_market_data_validation_invalid_price(self):
        """Test validation with invalid price."""
        # Test negative price
        invalid_data = MarketData(
            exchange="binance",
            symbol="btcusdt",
            timestamp="1640995200000",
            price=-100.0,
            volume=1.5
        )
        self.assertFalse(invalid_data.validate())
        
        # Test zero price
        invalid_data.price = 0.0
        self.assertFalse(invalid_data.validate())
    
    def test_market_data_validation_invalid_volume(self):
        """Test validation with invalid volume."""
        invalid_data = MarketData(
            exchange="binance",
            symbol="btcusdt",
            timestamp="1640995200000",
            price=50000.0,
            volume=-1.0
        )
        self.assertFalse(invalid_data.validate())
    
    def test_market_data_validation_missing_fields(self):
        """Test validation with missing required fields."""
        # Missing exchange
        invalid_data = MarketData(
            exchange="",
            symbol="btcusdt",
            timestamp="1640995200000",
            price=50000.0,
            volume=1.5
        )
        self.assertFalse(invalid_data.validate())
        
        # Missing symbol
        invalid_data = MarketData(
            exchange="binance",
            symbol="",
            timestamp="1640995200000",
            price=50000.0,
            volume=1.5
        )
        self.assertFalse(invalid_data.validate())
    
    def test_market_data_validation_price_range(self):
        """Test price range validation."""
        # Test price below minimum
        with patch.dict(os.environ, {"PRICE_VALIDATION_MIN": "100.0"}):
            invalid_data = MarketData(
                exchange="binance",
                symbol="btcusdt",
                timestamp="1640995200000",
                price=50.0,
                volume=1.5
            )
            self.assertFalse(invalid_data.validate())
        
        # Test price above maximum
        with patch.dict(os.environ, {"PRICE_VALIDATION_MAX": "1000.0"}):
            invalid_data = MarketData(
                exchange="binance",
                symbol="btcusdt",
                timestamp="1640995200000",
                price=50000.0,
                volume=1.5
            )
            self.assertFalse(invalid_data.validate())


class TestKinesisProducer(unittest.TestCase):
    """Test cases for KinesisProducer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.stream_name = "test-crypto-stream"
        self.region = "us-east-1"
        
        # Mock boto3 client
        self.mock_kinesis_client = Mock()
        self.mock_kinesis_client.describe_stream.return_value = {
            'StreamDescription': {
                'StreamStatus': 'ACTIVE'
            }
        }
    
    @patch('ingestion.producers.kinesis_producer.boto3')
    def test_kinesis_producer_initialization(self, mock_boto3):
        """Test KinesisProducer initialization."""
        mock_boto3.client.return_value = self.mock_kinesis_client
        
        producer = KinesisProducer(self.stream_name, self.region)
        
        self.assertEqual(producer.stream_name, self.stream_name)
        self.assertEqual(producer.region, self.region)
        self.assertEqual(producer.batch_size, 500)  # Default value
    
    @patch('ingestion.producers.kinesis_producer.boto3')
    def test_kinesis_producer_validation_success(self, mock_boto3):
        """Test successful stream validation."""
        mock_boto3.client.return_value = self.mock_kinesis_client
        
        producer = KinesisProducer(self.stream_name, self.region)
        
        # Verify describe_stream was called
        self.mock_kinesis_client.describe_stream.assert_called_once_with(
            StreamName=self.stream_name
        )
    
    @patch('ingestion.producers.kinesis_producer.boto3')
    def test_kinesis_producer_validation_failure(self, mock_boto3):
        """Test stream validation failure."""
        # Mock client that raises an exception
        mock_client = Mock()
        mock_client.describe_stream.side_effect = Exception("Stream not found")
        mock_boto3.client.return_value = mock_client
        
        with self.assertRaises(Exception):
            KinesisProducer(self.stream_name, self.region)
    
    @patch('ingestion.producers.kinesis_producer.boto3')
    def test_put_record_success(self, mock_boto3):
        """Test successful record insertion."""
        mock_boto3.client.return_value = self.mock_kinesis_client
        
        producer = KinesisProducer(self.stream_name, self.region)
        producer.batch_size = 1  # Small batch size for testing
        
        market_data = MarketData(
            exchange="binance",
            symbol="btcusdt",
            timestamp="1640995200000",
            price=50000.0,
            volume=1.5
        )
        
        # Mock successful put_records response
        self.mock_kinesis_client.put_records.return_value = {
            'FailedRecordCount': 0
        }
        
        result = producer.put_record(market_data)
        
        self.assertTrue(result)
        self.assertEqual(producer.total_records_sent, 1)
        self.assertEqual(producer.failed_records, 0)
    
    @patch('ingestion.producers.kinesis_producer.boto3')
    def test_put_record_failure(self, mock_boto3):
        """Test record insertion failure."""
        mock_boto3.client.return_value = self.mock_kinesis_client
        
        producer = KinesisProducer(self.stream_name, self.region)
        producer.batch_size = 1  # Small batch size for testing
        
        market_data = MarketData(
            exchange="binance",
            symbol="btcusdt",
            timestamp="1640995200000",
            price=50000.0,
            volume=1.5
        )
        
        # Mock failed put_records response
        self.mock_kinesis_client.put_records.side_effect = Exception("Kinesis error")
        
        result = producer.put_record(market_data)
        
        self.assertFalse(result)
        self.assertEqual(producer.total_records_sent, 0)
        self.assertEqual(producer.failed_records, 1)
    
    @patch('ingestion.producers.kinesis_producer.boto3')
    def test_flush_buffer(self, mock_boto3):
        """Test buffer flushing."""
        mock_boto3.client.return_value = self.mock_kinesis_client
        
        producer = KinesisProducer(self.stream_name, self.region)
        
        # Add records to buffer
        market_data1 = MarketData(
            exchange="binance",
            symbol="btcusdt",
            timestamp="1640995200000",
            price=50000.0,
            volume=1.5
        )
        market_data2 = MarketData(
            exchange="coinbase",
            symbol="btcusdt",
            timestamp="1640995201000",
            price=50001.0,
            volume=2.0
        )
        
        producer.records_buffer = [
            {
                'Data': json.dumps(market_data1.to_dict()),
                'PartitionKey': market_data1.symbol
            },
            {
                'Data': json.dumps(market_data2.to_dict()),
                'PartitionKey': market_data2.symbol
            }
        ]
        
        # Mock successful put_records response
        self.mock_kinesis_client.put_records.return_value = {
            'FailedRecordCount': 0
        }
        
        result = producer.flush()
        
        self.assertTrue(result)
        self.assertEqual(len(producer.records_buffer), 0)
        self.assertEqual(producer.total_records_sent, 2)
    
    @patch('ingestion.producers.kinesis_producer.boto3')
    def test_get_stats(self, mock_boto3):
        """Test statistics retrieval."""
        mock_boto3.client.return_value = self.mock_kinesis_client
        
        producer = KinesisProducer(self.stream_name, self.region)
        producer.total_records_sent = 100
        producer.failed_records = 5
        
        stats = producer.get_stats()
        
        self.assertEqual(stats['total_records_sent'], 100)
        self.assertEqual(stats['failed_records'], 5)
        self.assertEqual(stats['buffer_size'], 0)
        self.assertAlmostEqual(stats['success_rate'], 0.952, places=3)


class TestBinanceConnector(unittest.TestCase):
    """Test cases for BinanceConnector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.connector = BinanceConnector()
    
    def test_binance_connector_initialization(self):
        """Test BinanceConnector initialization."""
        self.assertEqual(self.connector.exchange_name, "binance")
        self.assertIn("stream.binance.com", self.connector.websocket_url)
        self.assertIn("btcusdt", self.connector.symbols)
    
    def test_process_binance_message_valid(self):
        """Test processing valid Binance message."""
        valid_message = json.dumps({
            'e': 'trade',
            's': 'BTCUSDT',
            'p': '50000.00',
            'q': '1.5',
            'T': 1640995200000,
            't': '12345'
        })
        
        result = self.connector.process_message(valid_message)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.exchange, "binance")
        self.assertEqual(result.symbol, "btcusdt")
        self.assertEqual(result.price, 50000.0)
        self.assertEqual(result.volume, 1.5)
        self.assertEqual(result.trade_id, "12345")
    
    def test_process_binance_message_invalid_event(self):
        """Test processing message with invalid event type."""
        invalid_message = json.dumps({
            'e': 'kline',  # Not a trade event
            's': 'BTCUSDT',
            'p': '50000.00',
            'q': '1.5',
            'T': 1640995200000
        })
        
        result = self.connector.process_message(invalid_message)
        
        self.assertIsNone(result)
    
    def test_process_binance_message_malformed(self):
        """Test processing malformed message."""
        malformed_message = "invalid json"
        
        result = self.connector.process_message(malformed_message)
        
        self.assertIsNone(result)
    
    def test_calculate_quality_score_perfect(self):
        """Test quality score calculation for perfect data."""
        data = {
            's': 'BTCUSDT',
            'p': '50000.00',
            'q': '1.5',
            'T': 1640995200000
        }
        
        score = self.connector._calculate_quality_score(data)
        
        self.assertEqual(score, 1.0)
    
    def test_calculate_quality_score_missing_fields(self):
        """Test quality score calculation with missing fields."""
        data = {
            's': 'BTCUSDT',
            'p': '50000.00'
            # Missing 'q' and 'T'
        }
        
        score = self.connector._calculate_quality_score(data)
        
        self.assertLess(score, 1.0)
        self.assertGreaterEqual(score, 0.0)


class TestCoinbaseConnector(unittest.TestCase):
    """Test cases for CoinbaseConnector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.connector = CoinbaseConnector()
    
    def test_coinbase_connector_initialization(self):
        """Test CoinbaseConnector initialization."""
        self.assertEqual(self.connector.exchange_name, "coinbase")
        self.assertIn("ws-feed.pro.coinbase.com", self.connector.websocket_url)
        self.assertIn("BTC-USD", self.connector.symbols)
    
    def test_process_coinbase_message_valid(self):
        """Test processing valid Coinbase message."""
        valid_message = json.dumps({
            'type': 'match',
            'product_id': 'BTC-USD',
            'price': '50000.00',
            'size': '1.5',
            'time': '2022-01-01T00:00:00.000Z',
            'trade_id': '12345'
        })
        
        result = self.connector.process_message(valid_message)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.exchange, "coinbase")
        self.assertEqual(result.symbol, "btcusd")
        self.assertEqual(result.price, 50000.0)
        self.assertEqual(result.volume, 1.5)
        self.assertEqual(result.trade_id, "12345")
    
    def test_process_coinbase_message_invalid_type(self):
        """Test processing message with invalid type."""
        invalid_message = json.dumps({
            'type': 'ticker',  # Not a match event
            'product_id': 'BTC-USD',
            'price': '50000.00',
            'size': '1.5'
        })
        
        result = self.connector.process_message(invalid_message)
        
        self.assertIsNone(result)
    
    def test_calculate_quality_score_perfect(self):
        """Test quality score calculation for perfect data."""
        data = {
            'product_id': 'BTC-USD',
            'price': '50000.00',
            'size': '1.5',
            'time': '2022-01-01T00:00:00.000Z'
        }
        
        score = self.connector._calculate_quality_score(data)
        
        self.assertEqual(score, 1.0)
    
    def test_calculate_quality_score_invalid_price(self):
        """Test quality score calculation with invalid price."""
        data = {
            'product_id': 'BTC-USD',
            'price': '-100.00',  # Negative price
            'size': '1.5',
            'time': '2022-01-01T00:00:00.000Z'
        }
        
        score = self.connector._calculate_quality_score(data)
        
        self.assertLess(score, 1.0)


class TestMarketDataStreamer(unittest.TestCase):
    """Test cases for MarketDataStreamer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.streamer = MarketDataStreamer()
    
    def test_streamer_initialization(self):
        """Test MarketDataStreamer initialization."""
        self.assertIsNotNone(self.streamer.producer)
        self.assertEqual(len(self.streamer.connectors), 2)
        self.assertFalse(self.streamer.running)
    
    def test_signal_handler(self):
        """Test signal handler functionality."""
        # Simulate signal
        self.streamer._signal_handler(2, None)  # SIGINT
        
        self.assertFalse(self.streamer.running)
    
    def test_streamer_stop(self):
        """Test streamer stop functionality."""
        self.streamer.running = True
        self.streamer.tasks = [Mock()]
        
        self.streamer.stop()
        
        self.assertFalse(self.streamer.running)
        # Verify task was cancelled
        self.streamer.tasks[0].cancel.assert_called_once()


if __name__ == '__main__':
    unittest.main() 