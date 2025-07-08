#!/usr/bin/env python3
"""
Crypto Analytics Dashboard - CloudWatch Dashboard Setup

This script creates comprehensive CloudWatch dashboards for monitoring
the crypto analytics platform performance, health, and costs.

Author: Crypto Analytics Team
Version: 1.0.0
"""

import boto3
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Initialize CloudWatch client
cloudwatch = boto3.client('cloudwatch')


class CloudWatchDashboardManager:
    """Manages CloudWatch dashboards for the crypto analytics platform."""
    
    def __init__(self, environment: str = "production"):
        """Initialize dashboard manager.
        
        Args:
            environment: Environment name (production, staging, development)
        """
        self.environment = environment
        self.namespace = "CryptoAnalytics"
        self.dashboard_prefix = f"CryptoAnalytics-{environment.title()}"
    
    def create_system_health_dashboard(self) -> str:
        """Create system health dashboard.
        
        Returns:
            Dashboard ARN
        """
        dashboard_body = {
            "widgets": [
                # Lambda Function Health
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Lambda", "Duration", "FunctionName", "crypto-stream-processor"],
                            [".", "Errors", ".", "."],
                            [".", "Invocations", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Lambda Function Performance",
                        "period": 300
                    }
                },
                # Kinesis Stream Health
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Kinesis", "GetRecords.IteratorAgeMilliseconds", "StreamName", "crypto-market-data"],
                            [".", "GetRecords.Records", ".", "."],
                            [".", "PutRecord.Records", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Kinesis Stream Performance",
                        "period": 300
                    }
                },
                # Redshift Cluster Health
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Redshift", "CPUUtilization", "ClusterIdentifier", "crypto-analytics"],
                            [".", "DatabaseConnections", ".", "."],
                            [".", "ReadIOPS", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Redshift Cluster Performance",
                        "period": 300
                    }
                },
                # S3 Storage Metrics
                {
                    "type": "metric",
                    "x": 12,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/S3", "NumberOfObjects", "BucketName", "crypto-analytics-data", "StorageType", "AllStorageTypes"],
                            [".", "BucketSizeBytes", ".", ".", ".", "."]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "S3 Storage Metrics",
                        "period": 3600
                    }
                }
            ]
        }
        
        return self._create_dashboard("SystemHealth", dashboard_body)
    
    def create_performance_dashboard(self) -> str:
        """Create performance monitoring dashboard.
        
        Returns:
            Dashboard ARN
        """
        dashboard_body = {
            "widgets": [
                # Records Processed
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "RecordsProcessed"],
                            [".", "RecordsFailed"],
                            [".", "ProcessingLatency"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Data Processing Performance",
                        "period": 300
                    }
                },
                # Data Quality Metrics
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "DataQualityScore"],
                            [".", "ValidationErrors"],
                            [".", "EnrichmentErrors"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Data Quality Metrics",
                        "period": 300
                    }
                },
                # Exchange Performance
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "ExchangeLatency", "Exchange", "binance"],
                            [".", ".", ".", "coinbase"],
                            [".", ".", ".", "kraken"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Exchange Connection Performance",
                        "period": 300
                    }
                },
                # Cost Metrics
                {
                    "type": "metric",
                    "x": 12,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Billing", "EstimatedCharges", "Currency", "USD"],
                            [self.namespace, "CostPerRecord"],
                            [".", "MonthlyCost"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Cost Metrics",
                        "period": 3600
                    }
                }
            ]
        }
        
        return self._create_dashboard("Performance", dashboard_body)
    
    def create_data_quality_dashboard(self) -> str:
        """Create data quality monitoring dashboard.
        
        Returns:
            Dashboard ARN
        """
        dashboard_body = {
            "widgets": [
                # Data Quality Score by Exchange
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "DataQualityScore", "Exchange", "binance"],
                            [".", ".", ".", "coinbase"],
                            [".", ".", ".", "kraken"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Data Quality Score by Exchange",
                        "period": 300
                    }
                },
                # Validation Error Types
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "ValidationErrors", "ErrorType", "missing_fields"],
                            [".", ".", ".", "invalid_price"],
                            [".", ".", ".", "invalid_timestamp"],
                            [".", ".", ".", "invalid_volume"]
                        ],
                        "view": "timeSeries",
                        "stacked": True,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Validation Error Types",
                        "period": 300
                    }
                },
                # Data Freshness
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "DataFreshnessSeconds"],
                            [".", "ProcessingDelay"],
                            [".", "IngestionLatency"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Data Freshness Metrics",
                        "period": 300
                    }
                },
                # Symbol Coverage
                {
                    "type": "metric",
                    "x": 12,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "SymbolCoverage", "Symbol", "BTCUSDT"],
                            [".", ".", ".", "ETHUSDT"],
                            [".", ".", ".", "BNBUSDT"],
                            [".", ".", ".", "ADAUSDT"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Symbol Coverage",
                        "period": 300
                    }
                }
            ]
        }
        
        return self._create_dashboard("DataQuality", dashboard_body)
    
    def create_cost_dashboard(self) -> str:
        """Create cost monitoring dashboard.
        
        Returns:
            Dashboard ARN
        """
        dashboard_body = {
            "widgets": [
                # Monthly Cost Breakdown
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Billing", "EstimatedCharges", "Service", "AmazonKinesis"],
                            [".", ".", ".", "AWSLambda"],
                            [".", ".", ".", "AmazonS3"],
                            [".", ".", ".", "AmazonRedshift"],
                            [".", ".", ".", "AWSGlue"]
                        ],
                        "view": "timeSeries",
                        "stacked": True,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Monthly Cost by Service",
                        "period": 86400
                    }
                },
                # Cost per Record
                {
                    "type": "metric",
                    "x": 12,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [self.namespace, "CostPerRecord"],
                            [".", "CostPerGB"],
                            [".", "CostPerQuery"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Cost Efficiency Metrics",
                        "period": 3600
                    }
                },
                # Resource Utilization
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            ["AWS/Lambda", "Duration", "FunctionName", "crypto-stream-processor"],
                            ["AWS/Kinesis", "GetRecords.IteratorAgeMilliseconds", "StreamName", "crypto-market-data"],
                            ["AWS/Redshift", "CPUUtilization", "ClusterIdentifier", "crypto-analytics"]
                        ],
                        "view": "timeSeries",
                        "stacked": False,
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Resource Utilization",
                        "period": 300
                    }
                },
                # Cost Alerts
                {
                    "type": "log",
                    "x": 12,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "query": "SOURCE 'crypto-cost-alerts'\n| fields @timestamp, @message\n| sort @timestamp desc\n| limit 100",
                        "region": os.getenv("AWS_REGION", "us-east-1"),
                        "title": "Cost Alert Logs",
                        "view": "table"
                    }
                }
            ]
        }
        
        return self._create_dashboard("Cost", dashboard_body)
    
    def _create_dashboard(self, dashboard_type: str, dashboard_body: Dict) -> str:
        """Create a CloudWatch dashboard.
        
        Args:
            dashboard_type: Type of dashboard
            dashboard_body: Dashboard configuration
            
        Returns:
            Dashboard ARN
        """
        dashboard_name = f"{self.dashboard_prefix}-{dashboard_type}"
        
        try:
            response = cloudwatch.put_dashboard(
                DashboardName=dashboard_name,
                DashboardBody=json.dumps(dashboard_body)
            )
            
            print(f"Created dashboard: {dashboard_name}")
            return response['DashboardArn']
            
        except Exception as e:
            print(f"Error creating dashboard {dashboard_name}: {str(e)}")
            raise
    
    def create_all_dashboards(self) -> Dict[str, str]:
        """Create all monitoring dashboards.
        
        Returns:
            Dictionary mapping dashboard types to ARNs
        """
        dashboards = {}
        
        try:
            dashboards['system_health'] = self.create_system_health_dashboard()
            dashboards['performance'] = self.create_performance_dashboard()
            dashboards['data_quality'] = self.create_data_quality_dashboard()
            dashboards['cost'] = self.create_cost_dashboard()
            
            print("All dashboards created successfully")
            return dashboards
            
        except Exception as e:
            print(f"Error creating dashboards: {str(e)}")
            raise


def main():
    """Main function to create CloudWatch dashboards."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create CloudWatch dashboards")
    parser.add_argument("--environment", default="production", 
                       choices=["production", "staging", "development"],
                       help="Environment name")
    parser.add_argument("--dashboard-type", 
                       choices=["all", "system_health", "performance", "data_quality", "cost"],
                       default="all",
                       help="Type of dashboard to create")
    
    args = parser.parse_args()
    
    try:
        manager = CloudWatchDashboardManager(args.environment)
        
        if args.dashboard_type == "all":
            dashboards = manager.create_all_dashboards()
            print("\nCreated dashboards:")
            for dashboard_type, arn in dashboards.items():
                print(f"  {dashboard_type}: {arn}")
        else:
            # Create specific dashboard
            if args.dashboard_type == "system_health":
                arn = manager.create_system_health_dashboard()
            elif args.dashboard_type == "performance":
                arn = manager.create_performance_dashboard()
            elif args.dashboard_type == "data_quality":
                arn = manager.create_data_quality_dashboard()
            elif args.dashboard_type == "cost":
                arn = manager.create_cost_dashboard()
            
            print(f"Created {args.dashboard_type} dashboard: {arn}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 