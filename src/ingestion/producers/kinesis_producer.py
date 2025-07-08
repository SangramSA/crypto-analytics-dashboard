#!/usr/bin/env python3
"""
Crypto Analytics Dashboard - Kinesis Data Producer

This module handles real-time streaming of cryptocurrency market data from multiple
exchanges to AWS Kinesis Data Streams. It supports Binance and Coinbase exchanges
with robust error handling, retry logic, and data quality validation.

Author: Crypto Analytics Team
Version: 1.0.0
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse

import boto3
import structlog
import websockets
from botocore.exceptions import ClientError, NoCredentialsError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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


@dataclass
class MarketData:
    """Market data structure for cryptocurrency trades."""
    
    exchange: str
    symbol: str
    timestamp: str
    price: float
    volume: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    trade_id: Optional[str] = None
    quality_score: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def validate(self) -> bool:
        """Validate market data quality."""
        if not all([self.exchange, self.symbol, self.timestamp, self.price > 0]):
            return False
        
        # Check price range
        min_price = float(os.getenv("PRICE_VALIDATION_MIN", "0.01"))
        max_price = float(os.getenv("PRICE_VALIDATION_MAX", "1000000.0"))
        if not (min_price <= self.price <= max_price):
            return False
        
        # Check volume
        min_volume = float(os.getenv("VOLUME_VALIDATION_MIN", "0.0"))
        if self.volume < min_volume:
            return False
        
        return True


class KinesisProducer:
    """Handles streaming data to AWS Kinesis Data Streams."""
    
    def __init__(self, stream_name: str, region: str = "us-east-1"):
        """Initialize Kinesis producer.
        
        Args:
            stream_name: Name of the Kinesis stream
            region: AWS region
        """
        self.stream_name = stream_name
        self.region = region
        self.client = boto3.client('kinesis', region_name=region)
        self.batch_size = int(os.getenv("KINESIS_BATCH_SIZE", "500"))
        self.max_retries = int(os.getenv("KINESIS_MAX_RETRIES", "3"))
        self.records_buffer: List[Dict] = []
        self.total_records_sent = 0
        self.failed_records = 0
        
        # Validate stream exists
        self._validate_stream()
    
    def _validate_stream(self) -> None:
        """Validate that the Kinesis stream exists."""
        try:
            response = self.client.describe_stream(StreamName=self.stream_name)
            logger.info(
                "Kinesis stream validated",
                stream_name=self.stream_name,
                status=response['StreamDescription']['StreamStatus']
            )
        except ClientError as e:
            logger.error(
                "Failed to validate Kinesis stream",
                stream_name=self.stream_name,
                error=str(e)
            )
            raise
    
    def put_record(self, market_data: MarketData) -> bool:
        """Put a single record to Kinesis.
        
        Args:
            market_data: Market data to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            record = {
                'Data': json.dumps(market_data.to_dict()),
                'PartitionKey': market_data.symbol
            }
            
            self.records_buffer.append(record)
            
            # Flush buffer if it reaches batch size
            if len(self.records_buffer) >= self.batch_size:
                return self._flush_buffer()
            
            return True
            
        except Exception as e:
            logger.error(
                "Failed to add record to buffer",
                error=str(e),
                market_data=market_data.to_dict()
            )
            self.failed_records += 1
            return False
    
    def _flush_buffer(self) -> bool:
        """Flush the records buffer to Kinesis."""
        if not self.records_buffer:
            return True
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.put_records(
                    Records=self.records_buffer,
                    StreamName=self.stream_name
                )
                
                # Check for failed records
                failed_count = response.get('FailedRecordCount', 0)
                if failed_count > 0:
                    logger.warning(
                        "Some records failed to send",
                        failed_count=failed_count,
                        total_records=len(self.records_buffer)
                    )
                    self.failed_records += failed_count
                
                self.total_records_sent += len(self.records_buffer) - failed_count
                self.records_buffer.clear()
                
                logger.debug(
                    "Successfully sent records to Kinesis",
                    records_sent=len(self.records_buffer) - failed_count,
                    total_sent=self.total_records_sent
                )
                
                return True
                
            except ClientError as e:
                logger.error(
                    "Failed to send records to Kinesis",
                    attempt=attempt + 1,
                    error=str(e)
                )
                if attempt == self.max_retries - 1:
                    self.failed_records += len(self.records_buffer)
                    self.records_buffer.clear()
                    return False
                
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return False
    
    def flush(self) -> bool:
        """Flush any remaining records in the buffer."""
        return self._flush_buffer()
    
    def get_stats(self) -> Dict:
        """Get producer statistics."""
        return {
            'total_records_sent': self.total_records_sent,
            'failed_records': self.failed_records,
            'buffer_size': len(self.records_buffer),
            'success_rate': (
                self.total_records_sent / (self.total_records_sent + self.failed_records)
                if (self.total_records_sent + self.failed_records) > 0 else 1.0
            )
        }


class ExchangeConnector:
    """Base class for exchange connectors."""
    
    def __init__(self, exchange_name: str, websocket_url: str):
        """Initialize exchange connector.
        
        Args:
            exchange_name: Name of the exchange
            websocket_url: WebSocket URL for the exchange
        """
        self.exchange_name = exchange_name
        self.websocket_url = websocket_url
        self.running = False
        self.reconnect_delay = 1
        self.max_reconnect_delay = 60
    
    async def connect(self) -> websockets.WebSocketServerProtocol:
        """Connect to the exchange WebSocket."""
        raise NotImplementedError
    
    async def process_message(self, message: str) -> Optional[MarketData]:
        """Process incoming WebSocket message."""
        raise NotImplementedError
    
    async def subscribe(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Subscribe to market data streams."""
        raise NotImplementedError


class BinanceConnector(ExchangeConnector):
    """Binance exchange connector."""
    
    def __init__(self):
        """Initialize Binance connector."""
        super().__init__(
            "binance",
            os.getenv("BINANCE_WEBSOCKET_URL", "wss://stream.binance.com:9443/ws/")
        )
        self.symbols = ["btcusdt", "ethusdt", "bnbusdt", "adausdt"]
    
    async def connect(self) -> websockets.WebSocketServerProtocol:
        """Connect to Binance WebSocket."""
        stream_names = [f"{symbol}@trade" for symbol in self.symbols]
        url = f"{self.websocket_url}{'/'.join(stream_names)}"
        
        logger.info("Connecting to Binance WebSocket", url=url)
        return await websockets.connect(url)
    
    async def process_message(self, message: str) -> Optional[MarketData]:
        """Process Binance trade message."""
        try:
            data = json.loads(message)
            
            if 'e' not in data or data['e'] != 'trade':
                return None
            
            return MarketData(
                exchange=self.exchange_name,
                symbol=data['s'].lower(),
                timestamp=str(data['T']),
                price=float(data['p']),
                volume=float(data['q']),
                trade_id=data.get('t'),
                quality_score=self._calculate_quality_score(data)
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to process Binance message", error=str(e), message=message)
            return None
    
    def _calculate_quality_score(self, data: Dict) -> float:
        """Calculate data quality score for Binance data."""
        score = 1.0
        
        # Check for required fields
        required_fields = ['s', 'p', 'q', 'T']
        for field in required_fields:
            if field not in data:
                score -= 0.2
        
        # Check price validity
        try:
            price = float(data['p'])
            if price <= 0:
                score -= 0.3
        except (ValueError, TypeError):
            score -= 0.3
        
        return max(0.0, score)
    
    async def subscribe(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Binance doesn't require explicit subscription for trade streams."""
        pass


class CoinbaseConnector(ExchangeConnector):
    """Coinbase exchange connector."""
    
    def __init__(self):
        """Initialize Coinbase connector."""
        super().__init__(
            "coinbase",
            os.getenv("COINBASE_WEBSOCKET_URL", "wss://ws-feed.pro.coinbase.com")
        )
        self.symbols = ["BTC-USD", "ETH-USD", "LTC-USD", "BCH-USD"]
    
    async def connect(self) -> websockets.WebSocketServerProtocol:
        """Connect to Coinbase WebSocket."""
        logger.info("Connecting to Coinbase WebSocket", url=self.websocket_url)
        return await websockets.connect(self.websocket_url)
    
    async def process_message(self, message: str) -> Optional[MarketData]:
        """Process Coinbase match message."""
        try:
            data = json.loads(message)
            
            if data.get('type') != 'match':
                return None
            
            return MarketData(
                exchange=self.exchange_name,
                symbol=data['product_id'].lower().replace('-', ''),
                timestamp=data['time'],
                price=float(data['price']),
                volume=float(data['size']),
                trade_id=data.get('trade_id'),
                quality_score=self._calculate_quality_score(data)
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to process Coinbase message", error=str(e), message=message)
            return None
    
    def _calculate_quality_score(self, data: Dict) -> float:
        """Calculate data quality score for Coinbase data."""
        score = 1.0
        
        # Check for required fields
        required_fields = ['product_id', 'price', 'size', 'time']
        for field in required_fields:
            if field not in data:
                score -= 0.2
        
        # Check price validity
        try:
            price = float(data['price'])
            if price <= 0:
                score -= 0.3
        except (ValueError, TypeError):
            score -= 0.3
        
        return max(0.0, score)
    
    async def subscribe(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Subscribe to Coinbase match messages."""
        subscribe_message = {
            "type": "subscribe",
            "product_ids": self.symbols,
            "channels": ["matches"]
        }
        
        await websocket.send(json.dumps(subscribe_message))
        logger.info("Subscribed to Coinbase channels", channels=["matches"])


class MarketDataStreamer:
    """Main orchestrator for streaming market data."""
    
    def __init__(self):
        """Initialize market data streamer."""
        self.producer = KinesisProducer(
            stream_name=os.getenv("KINESIS_STREAM_NAME", "crypto-market-data")
        )
        self.connectors = [
            BinanceConnector(),
            CoinbaseConnector()
        ]
        self.running = False
        self.tasks: List[asyncio.Task] = []
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal", signal=signum)
        self.running = False
    
    async def stream_exchange(self, connector: ExchangeConnector) -> None:
        """Stream data from a single exchange.
        
        Args:
            connector: Exchange connector to use
        """
        retry_count = 0
        max_retries = 10
        
        while self.running and retry_count < max_retries:
            try:
                websocket = await connector.connect()
                await connector.subscribe(websocket)
                
                logger.info(
                    "Successfully connected to exchange",
                    exchange=connector.exchange_name
                )
                
                async for message in websocket:
                    if not self.running:
                        break
                    
                    market_data = await connector.process_message(message)
                    if market_data and market_data.validate():
                        self.producer.put_record(market_data)
                
                retry_count = 0  # Reset retry count on successful connection
                
            except Exception as e:
                retry_count += 1
                logger.error(
                    "Exchange connection failed",
                    exchange=connector.exchange_name,
                    retry_count=retry_count,
                    error=str(e)
                )
                
                if retry_count < max_retries:
                    delay = min(2 ** retry_count, connector.max_reconnect_delay)
                    await asyncio.sleep(delay)
    
    async def start(self) -> None:
        """Start streaming from all exchanges."""
        self.running = True
        logger.info("Starting market data streaming")
        
        # Create tasks for each exchange
        for connector in self.connectors:
            task = asyncio.create_task(self.stream_exchange(connector))
            self.tasks.append(task)
        
        # Wait for all tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
    
    async def stop(self) -> None:
        """Stop streaming and cleanup."""
        logger.info("Stopping market data streaming")
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Flush any remaining records
        self.producer.flush()
        
        # Log final statistics
        stats = self.producer.get_stats()
        logger.info("Streaming completed", stats=stats)


async def main():
    """Main entry point."""
    try:
        # Validate AWS credentials
        try:
            boto3.client('sts').get_caller_identity()
        except NoCredentialsError:
            logger.error("AWS credentials not found. Please configure your credentials.")
            sys.exit(1)
        
        # Create and start streamer
        streamer = MarketDataStreamer()
        await streamer.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 