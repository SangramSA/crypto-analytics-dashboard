#!/usr/bin/env python3
"""
Crypto Analytics Dashboard - Glue ETL Job for OHLCV Aggregation

This Glue job reads raw market data from S3, aggregates it into OHLCV candles
at different time intervals, calculates technical indicators, and writes the
results to both S3 (Parquet) and Redshift.

Author: Crypto Analytics Team
Version: 1.0.0
"""

import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import boto3
import pandas as pd
from awsglue.context import GlueContext
from awsglue.dynamicframe import DynamicFrame
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, from_unixtime, hour, minute, second, year, month, dayofmonth,
    window, avg, sum, min, max, first, last, count, when, lit, udf
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, TimestampType,
    IntegerType, BooleanType
)

# Initialize Glue context
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# Configuration
S3_BUCKET = "crypto-analytics-data"
RAW_DATA_PREFIX = "raw/"
PROCESSED_DATA_PREFIX = "processed/"
REDSHIFT_CLUSTER = "crypto-analytics"
REDSHIFT_DATABASE = "crypto_analytics"
REDSHIFT_TABLE = "ohlcv_5min"

# Time intervals for aggregation (in minutes)
INTERVALS = [1, 5, 15, 60, 240, 1440]  # 1min, 5min, 15min, 1h, 4h, daily


class OHLCVAggregator:
    """Aggregates market data into OHLCV candles."""
    
    def __init__(self, spark_session):
        """Initialize aggregator.
        
        Args:
            spark_session: Spark session
        """
        self.spark = spark_session
        self.s3_bucket = S3_BUCKET
        self.raw_prefix = RAW_DATA_PREFIX
        self.processed_prefix = PROCESSED_DATA_PREFIX
    
    def read_raw_data(self, date_partition: str) -> DynamicFrame:
        """Read raw data from S3 for a specific date partition.
        
        Args:
            date_partition: Date partition string (YYYY/MM/DD)
            
        Returns:
            DynamicFrame containing raw data
        """
        try:
            # Read from S3
            raw_data = glueContext.create_dynamic_frame.from_options(
                connection_type="s3",
                connection_options={
                    "paths": [f"s3://{self.s3_bucket}/{self.raw_prefix}{date_partition}/"],
                    "recurse": True
                },
                format="json"
            )
            
            print(f"Read {raw_data.count()} records from S3")
            return raw_data
            
        except Exception as e:
            print(f"Error reading raw data: {str(e)}")
            raise
    
    def transform_to_dataframe(self, dynamic_frame: DynamicFrame):
        """Convert DynamicFrame to DataFrame and apply transformations.
        
        Args:
            dynamic_frame: Raw data DynamicFrame
            
        Returns:
            Transformed DataFrame
        """
        # Convert to DataFrame
        df = dynamic_frame.toDF()
        
        # Explode records array
        df = df.select(
            col("records").alias("records"),
            col("timestamp").alias("batch_timestamp"),
            col("partition").alias("data_partition")
        )
        
        # Explode the records array
        df = df.select(
            col("batch_timestamp"),
            col("data_partition"),
            col("records.*")
        )
        
        # Convert timestamp to proper format
        df = df.withColumn(
            "timestamp",
            from_unixtime(col("timestamp") / 1000)
        )
        
        # Add date/time columns for partitioning
        df = df.withColumn("year", year(col("timestamp")))
        df = df.withColumn("month", month(col("timestamp")))
        df = df.withColumn("day", dayofmonth(col("timestamp")))
        df = df.withColumn("hour", hour(col("timestamp")))
        df = df.withColumn("minute", minute(col("timestamp")))
        
        # Filter out invalid records
        df = df.filter(
            (col("price").isNotNull()) &
            (col("volume").isNotNull()) &
            (col("symbol").isNotNull()) &
            (col("exchange").isNotNull()) &
            (col("price") > 0) &
            (col("volume") >= 0)
        )
        
        # Cast numeric columns
        df = df.withColumn("price", col("price").cast(DoubleType()))
        df = df.withColumn("volume", col("volume").cast(DoubleType()))
        
        # Add calculated fields if available
        if "bid" in df.columns and "ask" in df.columns:
            df = df.withColumn("spread", col("ask") - col("bid"))
            df = df.withColumn("spread_percentage", 
                             when(col("bid") > 0, (col("spread") / col("bid")) * 100)
                             .otherwise(lit(None)))
        
        return df
    
    def aggregate_ohlcv(self, df, interval_minutes: int):
        """Aggregate data into OHLCV candles.
        
        Args:
            df: Input DataFrame
            interval_minutes: Time interval in minutes
            
        Returns:
            DataFrame with OHLCV data
        """
        # Create time window
        window_spec = window(
            col("timestamp"),
            f"{interval_minutes} minutes"
        )
        
        # Aggregate by symbol, exchange, and time window
        ohlcv_df = df.groupBy(
            col("symbol"),
            col("exchange"),
            window_spec
        ).agg(
            first(col("price")).alias("open"),
            max(col("price")).alias("high"),
            min(col("price")).alias("low"),
            last(col("price")).alias("close"),
            sum(col("volume")).alias("volume"),
            count(col("price")).alias("trade_count"),
            avg(col("price")).alias("vwap"),
            # Add spread metrics if available
            avg(col("spread")).alias("avg_spread"),
            avg(col("spread_percentage")).alias("avg_spread_percentage")
        )
        
        # Add interval information
        ohlcv_df = ohlcv_df.withColumn("interval_minutes", lit(interval_minutes))
        ohlcv_df = ohlcv_df.withColumn("interval_start", col("window.start"))
        ohlcv_df = ohlcv_df.withColumn("interval_end", col("window.end"))
        
        # Add date/time columns for partitioning
        ohlcv_df = ohlcv_df.withColumn("year", year(col("interval_start")))
        ohlcv_df = ohlcv_df.withColumn("month", month(col("interval_start")))
        ohlcv_df = ohlcv_df.withColumn("day", dayofmonth(col("interval_start")))
        ohlcv_df = ohlcv_df.withColumn("hour", hour(col("interval_start")))
        
        return ohlcv_df
    
    def calculate_technical_indicators(self, df):
        """Calculate technical indicators for OHLCV data.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with technical indicators
        """
        # Window functions for calculating indicators
        from pyspark.sql.window import Window
        from pyspark.sql.functions import lag, lead, stddev, mean
        
        # Create window spec ordered by timestamp
        window_spec = Window.partitionBy("symbol", "exchange").orderBy("interval_start")
        
        # Calculate price change
        df = df.withColumn("price_change", col("close") - lag("close", 1).over(window_spec))
        df = df.withColumn("price_change_percentage", 
                          when(lag("close", 1).over(window_spec) > 0,
                               (col("price_change") / lag("close", 1).over(window_spec)) * 100)
                          .otherwise(lit(None)))
        
        # Calculate moving averages
        df = df.withColumn("sma_5", avg("close").over(
            Window.partitionBy("symbol", "exchange").orderBy("interval_start").rowsBetween(-4, 0)
        ))
        df = df.withColumn("sma_10", avg("close").over(
            Window.partitionBy("symbol", "exchange").orderBy("interval_start").rowsBetween(-9, 0)
        ))
        df = df.withColumn("sma_20", avg("close").over(
            Window.partitionBy("symbol", "exchange").orderBy("interval_start").rowsBetween(-19, 0)
        ))
        
        # Calculate exponential moving averages
        df = df.withColumn("ema_12", self._calculate_ema("close", 12, window_spec))
        df = df.withColumn("ema_26", self._calculate_ema("close", 26, window_spec))
        
        # Calculate MACD
        df = df.withColumn("macd", col("ema_12") - col("ema_26"))
        df = df.withColumn("macd_signal", self._calculate_ema("macd", 9, window_spec))
        df = df.withColumn("macd_histogram", col("macd") - col("macd_signal"))
        
        # Calculate Bollinger Bands
        df = df.withColumn("bb_middle", avg("close").over(
            Window.partitionBy("symbol", "exchange").orderBy("interval_start").rowsBetween(-19, 0)
        ))
        df = df.withColumn("bb_std", stddev("close").over(
            Window.partitionBy("symbol", "exchange").orderBy("interval_start").rowsBetween(-19, 0)
        ))
        df = df.withColumn("bb_upper", col("bb_middle") + (col("bb_std") * 2))
        df = df.withColumn("bb_lower", col("bb_middle") - (col("bb_std") * 2))
        
        # Calculate RSI
        df = df.withColumn("rsi", self._calculate_rsi(window_spec))
        
        # Calculate volatility
        df = df.withColumn("volatility", stddev("close").over(
            Window.partitionBy("symbol", "exchange").orderBy("interval_start").rowsBetween(-19, 0)
        ))
        
        return df
    
    def _calculate_ema(self, column_name: str, period: int, window_spec):
        """Calculate Exponential Moving Average.
        
        Args:
            column_name: Column to calculate EMA for
            period: EMA period
            window_spec: Window specification
            
        Returns:
            Column with EMA values
        """
        alpha = 2.0 / (period + 1)
        
        # Initialize EMA with SMA
        ema_col = avg(col(column_name)).over(
            Window.partitionBy("symbol", "exchange").orderBy("interval_start").rowsBetween(-(period-1), 0)
        )
        
        # Apply EMA formula
        return when(
            lag(ema_col, 1).over(window_spec).isNotNull(),
            alpha * col(column_name) + (1 - alpha) * lag(ema_col, 1).over(window_spec)
        ).otherwise(ema_col)
    
    def _calculate_rsi(self, window_spec):
        """Calculate Relative Strength Index.
        
        Args:
            window_spec: Window specification
            
        Returns:
            Column with RSI values
        """
        # Calculate price changes
        price_change = col("close") - lag("close", 1).over(window_spec)
        
        # Separate gains and losses
        gains = when(price_change > 0, price_change).otherwise(0)
        losses = when(price_change < 0, -price_change).otherwise(0)
        
        # Calculate average gains and losses
        avg_gains = avg(gains).over(
            Window.partitionBy("symbol", "exchange").orderBy("interval_start").rowsBetween(-13, 0)
        )
        avg_losses = avg(losses).over(
            Window.partitionBy("symbol", "exchange").orderBy("interval_start").rowsBetween(-13, 0)
        )
        
        # Calculate RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def write_to_s3(self, df, interval_minutes: int, date_partition: str):
        """Write aggregated data to S3 in Parquet format.
        
        Args:
            df: DataFrame to write
            interval_minutes: Time interval
            date_partition: Date partition
        """
        try:
            # Write to S3 in Parquet format
            output_path = f"s3://{self.s3_bucket}/{self.processed_prefix}ohlcv_{interval_minutes}min/{date_partition}/"
            
            df.write.mode("overwrite").partitionBy("year", "month", "day").parquet(output_path)
            
            print(f"Successfully wrote {df.count()} records to S3: {output_path}")
            
        except Exception as e:
            print(f"Error writing to S3: {str(e)}")
            raise
    
    def write_to_redshift(self, df, table_name: str):
        """Write data to Redshift.
        
        Args:
            df: DataFrame to write
            table_name: Redshift table name
        """
        try:
            # Convert to DynamicFrame
            dynamic_frame = DynamicFrame.fromDF(df, glueContext, "redshift_data")
            
            # Write to Redshift
            glueContext.write_dynamic_frame.from_jdbc_conf(
                frame=dynamic_frame,
                catalog_connection="redshift-connection",
                connection_options={
                    "dbtable": table_name,
                    "database": REDSHIFT_DATABASE
                },
                transformation_ctx="redshift_write"
            )
            
            print(f"Successfully wrote {df.count()} records to Redshift table: {table_name}")
            
        except Exception as e:
            print(f"Error writing to Redshift: {str(e)}")
            raise
    
    def process_date_partition(self, date_partition: str):
        """Process a single date partition.
        
        Args:
            date_partition: Date partition string (YYYY/MM/DD)
        """
        print(f"Processing date partition: {date_partition}")
        
        # Read raw data
        raw_data = self.read_raw_data(date_partition)
        
        # Transform to DataFrame
        df = self.transform_to_dataframe(raw_data)
        
        if df.count() == 0:
            print(f"No data found for partition: {date_partition}")
            return
        
        # Process each time interval
        for interval in INTERVALS:
            print(f"Processing {interval}-minute intervals")
            
            # Aggregate to OHLCV
            ohlcv_df = self.aggregate_ohlcv(df, interval)
            
            # Calculate technical indicators
            ohlcv_df = self.calculate_technical_indicators(ohlcv_df)
            
            # Write to S3
            self.write_to_s3(ohlcv_df, interval, date_partition)
            
            # Write to Redshift for 5-minute intervals
            if interval == 5:
                self.write_to_redshift(ohlcv_df, f"ohlcv_{interval}min")
        
        print(f"Completed processing partition: {date_partition}")


def main():
    """Main function to run the Glue job."""
    try:
        # Get job parameters
        job_params = getResolvedOptions(sys.argv, [
            'JOB_NAME',
            'date_partition',
            's3_bucket',
            'raw_prefix',
            'processed_prefix'
        ])
        
        # Override configuration with job parameters
        date_partition = job_params.get('date_partition')
        if not date_partition:
            # Default to yesterday
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)
            date_partition = yesterday.strftime("%Y/%m/%d")
        
        s3_bucket = job_params.get('s3_bucket', S3_BUCKET)
        raw_prefix = job_params.get('raw_prefix', RAW_DATA_PREFIX)
        processed_prefix = job_params.get('processed_prefix', PROCESSED_DATA_PREFIX)
        
        print(f"Job parameters:")
        print(f"  Date partition: {date_partition}")
        print(f"  S3 bucket: {s3_bucket}")
        print(f"  Raw prefix: {raw_prefix}")
        print(f"  Processed prefix: {processed_prefix}")
        
        # Initialize aggregator
        aggregator = OHLCVAggregator(spark)
        aggregator.s3_bucket = s3_bucket
        aggregator.raw_prefix = raw_prefix
        aggregator.processed_prefix = processed_prefix
        
        # Process the date partition
        aggregator.process_date_partition(date_partition)
        
        print("Glue job completed successfully")
        
    except Exception as e:
        print(f"Glue job failed: {str(e)}")
        raise
    finally:
        job.commit()


if __name__ == "__main__":
    main() 