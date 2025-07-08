#!/usr/bin/env python3
"""
Crypto Analytics Dashboard - Health Check Script

This script performs comprehensive health checks on all components
of the crypto analytics platform and reports system status.

Author: Crypto Analytics Team
Version: 1.0.0
"""

import argparse
import boto3
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import psycopg2
import redis
import requests


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class HealthCheck:
    """Health check result."""
    component: str
    status: HealthStatus
    message: str
    details: Optional[Dict] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class HealthChecker:
    """Performs health checks on crypto analytics platform components."""
    
    def __init__(self, environment: str = "production"):
        """Initialize health checker.
        
        Args:
            environment: Environment name
        """
        self.environment = environment
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        # Initialize AWS clients
        self.lambda_client = boto3.client('lambda', region_name=self.region)
        self.kinesis_client = boto3.client('kinesis', region_name=self.region)
        self.s3_client = boto3.client('s3', region_name=self.region)
        self.redshift_client = boto3.client('redshift', region_name=self.region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        self.glue_client = boto3.client('glue', region_name=self.region)
    
    def check_lambda_function(self) -> HealthCheck:
        """Check Lambda function health.
        
        Returns:
            Health check result
        """
        try:
            function_name = f"crypto-stream-processor-{self.environment}"
            
            # Get function configuration
            response = self.lambda_client.get_function(
                FunctionName=function_name
            )
            
            # Check function state
            state = response['Configuration']['State']
            if state != 'Active':
                return HealthCheck(
                    component="Lambda Function",
                    status=HealthStatus.CRITICAL,
                    message=f"Function {function_name} is in {state} state",
                    details={'function_name': function_name, 'state': state}
                )
            
            # Check recent errors
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)
            
            error_metrics = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Errors',
                Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Sum']
            )
            
            error_count = error_metrics['Datapoints'][0]['Sum'] if error_metrics['Datapoints'] else 0
            
            if error_count > 10:
                return HealthCheck(
                    component="Lambda Function",
                    status=HealthStatus.CRITICAL,
                    message=f"High error rate: {error_count} errors in last 5 minutes",
                    details={'function_name': function_name, 'error_count': error_count}
                )
            elif error_count > 5:
                return HealthCheck(
                    component="Lambda Function",
                    status=HealthStatus.WARNING,
                    message=f"Elevated error rate: {error_count} errors in last 5 minutes",
                    details={'function_name': function_name, 'error_count': error_count}
                )
            
            return HealthCheck(
                component="Lambda Function",
                status=HealthStatus.HEALTHY,
                message=f"Function {function_name} is healthy",
                details={'function_name': function_name, 'error_count': error_count}
            )
            
        except Exception as e:
            return HealthCheck(
                component="Lambda Function",
                status=HealthStatus.UNKNOWN,
                message=f"Error checking Lambda function: {str(e)}",
                details={'error': str(e)}
            )
    
    def check_kinesis_stream(self) -> HealthCheck:
        """Check Kinesis stream health.
        
        Returns:
            Health check result
        """
        try:
            stream_name = f"crypto-market-data-{self.environment}"
            
            # Get stream description
            response = self.kinesis_client.describe_stream(
                StreamName=stream_name
            )
            
            stream_status = response['StreamDescription']['StreamStatus']
            if stream_status != 'ACTIVE':
                return HealthCheck(
                    component="Kinesis Stream",
                    status=HealthStatus.CRITICAL,
                    message=f"Stream {stream_name} is in {stream_status} state",
                    details={'stream_name': stream_name, 'status': stream_status}
                )
            
            # Check iterator age
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)
            
            iterator_metrics = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Kinesis',
                MetricName='GetRecords.IteratorAgeMilliseconds',
                Dimensions=[{'Name': 'StreamName', 'Value': stream_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Maximum']
            )
            
            max_iterator_age = iterator_metrics['Datapoints'][0]['Maximum'] if iterator_metrics['Datapoints'] else 0
            
            if max_iterator_age > 300000:  # 5 minutes
                return HealthCheck(
                    component="Kinesis Stream",
                    status=HealthStatus.CRITICAL,
                    message=f"High iterator age: {max_iterator_age/1000:.1f} seconds",
                    details={'stream_name': stream_name, 'iterator_age_ms': max_iterator_age}
                )
            elif max_iterator_age > 60000:  # 1 minute
                return HealthCheck(
                    component="Kinesis Stream",
                    status=HealthStatus.WARNING,
                    message=f"Elevated iterator age: {max_iterator_age/1000:.1f} seconds",
                    details={'stream_name': stream_name, 'iterator_age_ms': max_iterator_age}
                )
            
            return HealthCheck(
                component="Kinesis Stream",
                status=HealthStatus.HEALTHY,
                message=f"Stream {stream_name} is healthy",
                details={'stream_name': stream_name, 'iterator_age_ms': max_iterator_age}
            )
            
        except Exception as e:
            return HealthCheck(
                component="Kinesis Stream",
                status=HealthStatus.UNKNOWN,
                message=f"Error checking Kinesis stream: {str(e)}",
                details={'error': str(e)}
            )
    
    def check_s3_bucket(self) -> HealthCheck:
        """Check S3 bucket health.
        
        Returns:
            Health check result
        """
        try:
            bucket_name = f"crypto-analytics-data-{self.environment}"
            
            # Check if bucket exists and is accessible
            self.s3_client.head_bucket(Bucket=bucket_name)
            
            # Get bucket metrics
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)
            
            size_metrics = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='BucketSizeBytes',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket_name},
                    {'Name': 'StorageType', 'Value': 'StandardStorage'}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,
                Statistics=['Average']
            )
            
            bucket_size = size_metrics['Datapoints'][0]['Average'] if size_metrics['Datapoints'] else 0
            size_gb = bucket_size / (1024**3)
            
            if size_gb > 100:  # 100 GB
                return HealthCheck(
                    component="S3 Bucket",
                    status=HealthStatus.WARNING,
                    message=f"Large bucket size: {size_gb:.1f} GB",
                    details={'bucket_name': bucket_name, 'size_gb': size_gb}
                )
            
            return HealthCheck(
                component="S3 Bucket",
                status=HealthStatus.HEALTHY,
                message=f"Bucket {bucket_name} is healthy",
                details={'bucket_name': bucket_name, 'size_gb': size_gb}
            )
            
        except Exception as e:
            return HealthCheck(
                component="S3 Bucket",
                status=HealthStatus.UNKNOWN,
                message=f"Error checking S3 bucket: {str(e)}",
                details={'error': str(e)}
            )
    
    def check_redshift_cluster(self) -> HealthCheck:
        """Check Redshift cluster health.
        
        Returns:
            Health check result
        """
        try:
            cluster_id = f"crypto-analytics-{self.environment}"
            
            # Get cluster status
            response = self.redshift_client.describe_clusters(
                ClusterIdentifier=cluster_id
            )
            
            if not response['Clusters']:
                return HealthCheck(
                    component="Redshift Cluster",
                    status=HealthStatus.CRITICAL,
                    message=f"Cluster {cluster_id} not found",
                    details={'cluster_id': cluster_id}
                )
            
            cluster = response['Clusters'][0]
            cluster_status = cluster['ClusterStatus']
            
            if cluster_status != 'available':
                return HealthCheck(
                    component="Redshift Cluster",
                    status=HealthStatus.CRITICAL,
                    message=f"Cluster {cluster_id} is in {cluster_status} state",
                    details={'cluster_id': cluster_id, 'status': cluster_status}
                )
            
            # Check CPU utilization
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)
            
            cpu_metrics = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Redshift',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'ClusterIdentifier', 'Value': cluster_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Maximum']
            )
            
            max_cpu = cpu_metrics['Datapoints'][0]['Maximum'] if cpu_metrics['Datapoints'] else 0
            
            if max_cpu > 80:
                return HealthCheck(
                    component="Redshift Cluster",
                    status=HealthStatus.CRITICAL,
                    message=f"High CPU utilization: {max_cpu:.1f}%",
                    details={'cluster_id': cluster_id, 'cpu_utilization': max_cpu}
                )
            elif max_cpu > 60:
                return HealthCheck(
                    component="Redshift Cluster",
                    status=HealthStatus.WARNING,
                    message=f"Elevated CPU utilization: {max_cpu:.1f}%",
                    details={'cluster_id': cluster_id, 'cpu_utilization': max_cpu}
                )
            
            return HealthCheck(
                component="Redshift Cluster",
                status=HealthStatus.HEALTHY,
                message=f"Cluster {cluster_id} is healthy",
                details={'cluster_id': cluster_id, 'cpu_utilization': max_cpu}
            )
            
        except Exception as e:
            return HealthCheck(
                component="Redshift Cluster",
                status=HealthStatus.UNKNOWN,
                message=f"Error checking Redshift cluster: {str(e)}",
                details={'error': str(e)}
            )
    
    def check_database_connection(self) -> HealthCheck:
        """Check database connection health.
        
        Returns:
            Health check result
        """
        try:
            if self.environment == "development":
                # Use local PostgreSQL for development
                conn = psycopg2.connect(
                    host="localhost",
                    port=5432,
                    database="crypto_analytics",
                    user="admin",
                    password="password"
                )
            else:
                # Use Redshift for production/staging
                cluster_id = f"crypto-analytics-{self.environment}"
                response = self.redshift_client.describe_clusters(
                    ClusterIdentifier=cluster_id
                )
                cluster = response['Clusters'][0]
                endpoint = cluster['Endpoint']['Address']
                port = cluster['Endpoint']['Port']
                
                conn = psycopg2.connect(
                    host=endpoint,
                    port=port,
                    database="crypto_analytics",
                    user="admin",
                    password=os.getenv("REDSHIFT_PASSWORD")
                )
            
            # Test connection with a simple query
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM analytics.ohlcv_5min WHERE interval_start >= NOW() - INTERVAL '1 hour'")
            recent_records = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            if recent_records == 0:
                return HealthCheck(
                    component="Database Connection",
                    status=HealthStatus.WARNING,
                    message="No recent data found in database",
                    details={'recent_records': recent_records}
                )
            
            return HealthCheck(
                component="Database Connection",
                status=HealthStatus.HEALTHY,
                message="Database connection is healthy",
                details={'recent_records': recent_records}
            )
            
        except Exception as e:
            return HealthCheck(
                component="Database Connection",
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                details={'error': str(e)}
            )
    
    def check_redis_connection(self) -> HealthCheck:
        """Check Redis connection health.
        
        Returns:
            Health check result
        """
        try:
            if self.environment == "development":
                redis_client = redis.Redis(host='localhost', port=6379, db=0)
            else:
                # Use ElastiCache in production
                redis_client = redis.Redis(
                    host=os.getenv("REDIS_HOST"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    password=os.getenv("REDIS_PASSWORD"),
                    db=0
                )
            
            # Test connection
            redis_client.ping()
            
            # Check memory usage
            info = redis_client.info('memory')
            used_memory_mb = info['used_memory'] / (1024**2)
            
            if used_memory_mb > 100:  # 100 MB
                return HealthCheck(
                    component="Redis Connection",
                    status=HealthStatus.WARNING,
                    message=f"High memory usage: {used_memory_mb:.1f} MB",
                    details={'used_memory_mb': used_memory_mb}
                )
            
            return HealthCheck(
                component="Redis Connection",
                status=HealthStatus.HEALTHY,
                message="Redis connection is healthy",
                details={'used_memory_mb': used_memory_mb}
            )
            
        except Exception as e:
            return HealthCheck(
                component="Redis Connection",
                status=HealthStatus.CRITICAL,
                message=f"Redis connection failed: {str(e)}",
                details={'error': str(e)}
            )
    
    def check_data_quality(self) -> HealthCheck:
        """Check data quality metrics.
        
        Returns:
            Health check result
        """
        try:
            # Get data quality metrics from CloudWatch
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=5)
            
            quality_metrics = self.cloudwatch.get_metric_statistics(
                Namespace='CryptoAnalytics',
                MetricName='DataQualityScore',
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if not quality_metrics['Datapoints']:
                return HealthCheck(
                    component="Data Quality",
                    status=HealthStatus.UNKNOWN,
                    message="No data quality metrics available",
                    details={}
                )
            
            avg_quality_score = quality_metrics['Datapoints'][0]['Average']
            
            if avg_quality_score < 0.7:
                return HealthCheck(
                    component="Data Quality",
                    status=HealthStatus.CRITICAL,
                    message=f"Low data quality score: {avg_quality_score:.2f}",
                    details={'quality_score': avg_quality_score}
                )
            elif avg_quality_score < 0.8:
                return HealthCheck(
                    component="Data Quality",
                    status=HealthStatus.WARNING,
                    message=f"Below target data quality score: {avg_quality_score:.2f}",
                    details={'quality_score': avg_quality_score}
                )
            
            return HealthCheck(
                component="Data Quality",
                status=HealthStatus.HEALTHY,
                message=f"Data quality is good: {avg_quality_score:.2f}",
                details={'quality_score': avg_quality_score}
            )
            
        except Exception as e:
            return HealthCheck(
                component="Data Quality",
                status=HealthStatus.UNKNOWN,
                message=f"Error checking data quality: {str(e)}",
                details={'error': str(e)}
            )
    
    def run_all_checks(self) -> List[HealthCheck]:
        """Run all health checks.
        
        Returns:
            List of health check results
        """
        checks = [
            self.check_lambda_function(),
            self.check_kinesis_stream(),
            self.check_s3_bucket(),
            self.check_redshift_cluster(),
            self.check_database_connection(),
            self.check_redis_connection(),
            self.check_data_quality()
        ]
        
        return checks
    
    def print_summary(self, checks: List[HealthCheck]) -> None:
        """Print health check summary.
        
        Args:
            checks: List of health check results
        """
        print(f"\n{'='*60}")
        print(f"CRYPTO ANALYTICS DASHBOARD - HEALTH CHECK")
        print(f"Environment: {self.environment.upper()}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'='*60}")
        
        # Group by status
        status_groups = {}
        for check in checks:
            status = check.status.value
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(check)
        
        # Print by status (CRITICAL first, then WARNING, then HEALTHY, then UNKNOWN)
        status_order = ['CRITICAL', 'WARNING', 'HEALTHY', 'UNKNOWN']
        
        for status in status_order:
            if status in status_groups:
                print(f"\n{status} ({len(status_groups[status])} components):")
                print("-" * 40)
                
                for check in status_groups[status]:
                    print(f"  • {check.component}: {check.message}")
                    if check.details:
                        for key, value in check.details.items():
                            print(f"    {key}: {value}")
        
        # Overall status
        critical_count = len(status_groups.get('CRITICAL', []))
        warning_count = len(status_groups.get('WARNING', []))
        
        if critical_count > 0:
            overall_status = "CRITICAL"
        elif warning_count > 0:
            overall_status = "WARNING"
        else:
            overall_status = "HEALTHY"
        
        print(f"\n{'='*60}")
        print(f"OVERALL STATUS: {overall_status}")
        print(f"{'='*60}")


def main():
    """Main function to run health checks."""
    parser = argparse.ArgumentParser(description="Run health checks for crypto analytics platform")
    parser.add_argument("--environment", default="production",
                       choices=["production", "staging", "development"],
                       help="Environment to check")
    parser.add_argument("--component", 
                       choices=["all", "lambda", "kinesis", "s3", "redshift", "database", "redis", "data-quality"],
                       default="all",
                       help="Specific component to check")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                       help="Output format")
    
    args = parser.parse_args()
    
    try:
        checker = HealthChecker(args.environment)
        
        if args.component == "all":
            checks = checker.run_all_checks()
        else:
            # Run specific component check
            if args.component == "lambda":
                checks = [checker.check_lambda_function()]
            elif args.component == "kinesis":
                checks = [checker.check_kinesis_stream()]
            elif args.component == "s3":
                checks = [checker.check_s3_bucket()]
            elif args.component == "redshift":
                checks = [checker.check_redshift_cluster()]
            elif args.component == "database":
                checks = [checker.check_database_connection()]
            elif args.component == "redis":
                checks = [checker.check_redis_connection()]
            elif args.component == "data-quality":
                checks = [checker.check_data_quality()]
        
        if args.format == "json":
            # Output as JSON
            results = []
            for check in checks:
                results.append({
                    'component': check.component,
                    'status': check.status.value,
                    'message': check.message,
                    'details': check.details,
                    'timestamp': check.timestamp.isoformat()
                })
            print(json.dumps(results, indent=2))
        else:
            # Output as text
            checker.print_summary(checks)
        
        # Exit with appropriate code
        critical_count = sum(1 for check in checks if check.status == HealthStatus.CRITICAL)
        if critical_count > 0:
            sys.exit(2)  # Critical
        elif any(check.status == HealthStatus.WARNING for check in checks):
            sys.exit(1)  # Warning
        else:
            sys.exit(0)  # Healthy
            
    except Exception as e:
        print(f"Error running health checks: {str(e)}")
        sys.exit(3)  # Error


if __name__ == "__main__":
    main() 