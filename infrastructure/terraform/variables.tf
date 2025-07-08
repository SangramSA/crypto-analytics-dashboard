# Crypto Analytics Dashboard - Terraform Variables
# This file defines all variables used in the Terraform configuration

# AWS Configuration
variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones to use"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
}

# S3 Configuration
variable "s3_bucket_name" {
  description = "Name of the S3 bucket for data lake"
  type        = string
  default     = "crypto-analytics-data"
}

# Kinesis Configuration
variable "kinesis_stream_name" {
  description = "Name of the Kinesis data stream"
  type        = string
  default     = "crypto-market-data"
}

variable "kinesis_shard_count" {
  description = "Number of shards for Kinesis stream"
  type        = number
  default     = 10
}

variable "kinesis_retention_period" {
  description = "Data retention period in hours"
  type        = number
  default     = 24
}

variable "kinesis_min_shards" {
  description = "Minimum number of shards for auto-scaling"
  type        = number
  default     = 5
}

variable "kinesis_max_shards" {
  description = "Maximum number of shards for auto-scaling"
  type        = number
  default     = 20
}

# Lambda Configuration
variable "lambda_function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = "crypto-stream-processor"
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.9"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 60
}

variable "lambda_memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 512
}

variable "lambda_batch_size" {
  description = "Lambda batch size for Kinesis processing"
  type        = number
  default     = 500
}

# Redshift Configuration
variable "redshift_cluster_id" {
  description = "Redshift cluster identifier"
  type        = string
  default     = "crypto-analytics"
}

variable "redshift_database" {
  description = "Redshift database name"
  type        = string
  default     = "crypto_analytics"
}

variable "redshift_username" {
  description = "Redshift master username"
  type        = string
  default     = "admin"
}

variable "redshift_password" {
  description = "Redshift master password"
  type        = string
  sensitive   = true
}

variable "redshift_node_type" {
  description = "Redshift node type"
  type        = string
  default     = "dc2.large"
}

variable "redshift_nodes" {
  description = "Number of Redshift nodes"
  type        = number
  default     = 2
}

variable "redshift_snapshot_identifier" {
  description = "Redshift snapshot identifier for restore"
  type        = string
  default     = null
}

# Glue Configuration
variable "glue_database_name" {
  description = "Glue database name"
  type        = string
  default     = "crypto_analytics"
}

variable "glue_crawler_name" {
  description = "Glue crawler name"
  type        = string
  default     = "crypto-data-crawler"
}

variable "glue_job_name" {
  description = "Glue ETL job name"
  type        = string
  default     = "ohlcv-aggregation"
}

variable "glue_worker_type" {
  description = "Glue worker type"
  type        = string
  default     = "G.1X"
}

variable "glue_num_workers" {
  description = "Number of Glue workers"
  type        = number
  default     = 2
}

variable "glue_timeout" {
  description = "Glue job timeout in minutes"
  type        = number
  default     = 60
}

# CloudWatch Configuration
variable "cloudwatch_dashboard_name" {
  description = "CloudWatch dashboard name"
  type        = string
  default     = "CryptoAnalytics"
}

# SNS Configuration
variable "sns_email_subscriptions" {
  description = "List of email addresses for SNS subscriptions"
  type        = list(string)
  default     = []
}

# QuickSight Configuration
variable "quicksight_user_arn" {
  description = "QuickSight user ARN"
  type        = string
  default     = ""
}

# Tags
variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "crypto-analytics-dashboard"
    ManagedBy   = "terraform"
    CostCenter  = "analytics"
  }
}

# Performance Configuration
variable "enable_auto_scaling" {
  description = "Enable auto-scaling for Kinesis"
  type        = bool
  default     = false
}

variable "enable_monitoring" {
  description = "Enable detailed monitoring"
  type        = bool
  default     = true
}

variable "enable_backup" {
  description = "Enable backup and recovery"
  type        = bool
  default     = true
}

# Security Configuration
variable "enable_encryption" {
  description = "Enable encryption at rest"
  type        = bool
  default     = true
}

variable "enable_vpc_endpoints" {
  description = "Enable VPC endpoints for AWS services"
  type        = bool
  default     = false
}

# Cost Optimization
variable "enable_spot_instances" {
  description = "Use spot instances for cost optimization"
  type        = bool
  default     = false
}

variable "enable_schedule_pause" {
  description = "Enable scheduled pause for non-production environments"
  type        = bool
  default     = true
}

# Data Retention
variable "raw_data_retention_days" {
  description = "Retention period for raw data in days"
  type        = number
  default     = 90
}

variable "processed_data_retention_days" {
  description = "Retention period for processed data in days"
  type        = number
  default     = 365
}

# Monitoring and Alerting
variable "alert_thresholds" {
  description = "Alert thresholds for monitoring"
  type        = map(number)
  default = {
    lambda_error_rate     = 1.0
    kinesis_iterator_age  = 60
    redshift_cpu_usage    = 80
    data_quality_score    = 0.8
    cost_threshold        = 200
  }
}

variable "monitoring_interval" {
  description = "Monitoring interval in seconds"
  type        = number
  default     = 300
}

# Development Configuration
variable "enable_localstack" {
  description = "Enable LocalStack for local development"
  type        = bool
  default     = false
}

variable "localstack_endpoint" {
  description = "LocalStack endpoint URL"
  type        = string
  default     = "http://localhost:4566"
} 