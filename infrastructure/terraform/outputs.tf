# Crypto Analytics Dashboard - Terraform Outputs
# This file defines all outputs from the Terraform configuration

# Kinesis Outputs
output "kinesis_stream_arn" {
  description = "ARN of the Kinesis data stream"
  value       = module.kinesis.stream_arn
}

output "kinesis_stream_name" {
  description = "Name of the Kinesis data stream"
  value       = module.kinesis.stream_name
}

output "kinesis_stream_url" {
  description = "URL for Kinesis stream monitoring"
  value       = "https://console.aws.amazon.com/kinesis/home?region=${var.aws_region}#/streams/details/${var.kinesis_stream_name}"
}

# Lambda Outputs
output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = module.lambda.function_arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = module.lambda.function_name
}

output "lambda_function_url" {
  description = "URL for Lambda function monitoring"
  value       = "https://console.aws.amazon.com/lambda/home?region=${var.aws_region}#/functions/${var.lambda_function_name}"
}

# S3 Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = module.s3.bucket_name
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = module.s3.bucket_arn
}

output "s3_bucket_url" {
  description = "URL for S3 bucket"
  value       = "https://console.aws.amazon.com/s3/buckets/${var.s3_bucket_name}?region=${var.aws_region}"
}

# Redshift Outputs
output "redshift_cluster_id" {
  description = "Redshift cluster identifier"
  value       = module.redshift.cluster_id
}

output "redshift_cluster_endpoint" {
  description = "Redshift cluster endpoint"
  value       = module.redshift.cluster_endpoint
}

output "redshift_database_name" {
  description = "Redshift database name"
  value       = var.redshift_database
}

output "redshift_connection_string" {
  description = "Redshift connection string"
  value       = "postgresql://${var.redshift_username}:${var.redshift_password}@${module.redshift.cluster_endpoint}:5439/${var.redshift_database}"
  sensitive   = true
}

output "redshift_url" {
  description = "URL for Redshift cluster monitoring"
  value       = "https://console.aws.amazon.com/redshift/home?region=${var.aws_region}#cluster:clusterId=${var.redshift_cluster_id}"
}

# Glue Outputs
output "glue_database_name" {
  description = "Glue database name"
  value       = module.glue.database_name
}

output "glue_crawler_name" {
  description = "Glue crawler name"
  value       = module.glue.crawler_name
}

output "glue_job_name" {
  description = "Glue ETL job name"
  value       = module.glue.job_name
}

output "glue_url" {
  description = "URL for Glue console"
  value       = "https://console.aws.amazon.com/glue/home?region=${var.aws_region}#/catalog/databases/${var.glue_database_name}"
}

# CloudWatch Outputs
output "cloudwatch_dashboard_name" {
  description = "CloudWatch dashboard name"
  value       = module.cloudwatch.dashboard_name
}

output "cloudwatch_dashboard_url" {
  description = "URL of the CloudWatch dashboard"
  value       = module.cloudwatch.dashboard_url
}

output "cloudwatch_log_groups" {
  description = "CloudWatch log groups"
  value       = module.cloudwatch.log_groups
}

# SNS Outputs
output "sns_topic_arn" {
  description = "ARN of the SNS topic"
  value       = module.sns.topic_arn
}

output "sns_topic_name" {
  description = "Name of the SNS topic"
  value       = module.sns.topic_name
}

# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = module.vpc.vpc_cidr_block
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnet_ids
}

# Security Group Outputs
output "lambda_security_group_id" {
  description = "ID of the Lambda security group"
  value       = module.security_groups.lambda_security_group_id
}

output "redshift_security_group_id" {
  description = "ID of the Redshift security group"
  value       = module.security_groups.redshift_security_group_id
}

# IAM Outputs
output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = module.iam.lambda_role_arn
}

output "glue_role_arn" {
  description = "ARN of the Glue execution role"
  value       = module.iam.glue_role_arn
}

output "redshift_role_arn" {
  description = "ARN of the Redshift execution role"
  value       = module.iam.redshift_role_arn
}

# QuickSight Outputs
output "quicksight_datasource_arn" {
  description = "ARN of the QuickSight data source"
  value       = module.quicksight.datasource_arn
}

output "quicksight_datasource_name" {
  description = "Name of the QuickSight data source"
  value       = module.quicksight.datasource_name
}

# Application URLs
output "application_urls" {
  description = "URLs for various application components"
  value = {
    kinesis_console = "https://console.aws.amazon.com/kinesis/home?region=${var.aws_region}#/streams/details/${var.kinesis_stream_name}"
    lambda_console  = "https://console.aws.amazon.com/lambda/home?region=${var.aws_region}#/functions/${var.lambda_function_name}"
    s3_console      = "https://console.aws.amazon.com/s3/buckets/${var.s3_bucket_name}?region=${var.aws_region}"
    redshift_console = "https://console.aws.amazon.com/redshift/home?region=${var.aws_region}#cluster:clusterId=${var.redshift_cluster_id}"
    glue_console    = "https://console.aws.amazon.com/glue/home?region=${var.aws_region}#/catalog/databases/${var.glue_database_name}"
    cloudwatch_dashboard = module.cloudwatch.dashboard_url
  }
}

# Connection Information
output "connection_info" {
  description = "Connection information for the application"
  value = {
    kinesis_stream_name = var.kinesis_stream_name
    s3_bucket_name     = var.s3_bucket_name
    redshift_endpoint  = module.redshift.cluster_endpoint
    redshift_database  = var.redshift_database
    redshift_username  = var.redshift_username
    glue_database      = var.glue_database_name
    cloudwatch_namespace = "CryptoAnalytics"
  }
}

# Cost Estimation
output "estimated_monthly_cost" {
  description = "Estimated monthly cost breakdown"
  value = {
    kinesis = "~$50-100 (depending on throughput)"
    lambda  = "~$20-50 (depending on invocations)"
    s3      = "~$10-30 (depending on data volume)"
    redshift = "~$200-400 (dc2.large, 2 nodes)"
    glue    = "~$50-100 (depending on job frequency)"
    cloudwatch = "~$10-20"
    sns     = "~$1-5"
    total   = "~$341-705/month"
  }
}

# Performance Metrics
output "performance_targets" {
  description = "Performance targets for the application"
  value = {
    ingestion_throughput = "2000 records/minute sustained"
    processing_latency   = "<1 second from ingestion to S3"
    query_performance    = "<3 seconds for common queries"
    data_freshness       = "5-minute candles available within 10 seconds"
    system_uptime        = "99.9% availability"
  }
}

# Security Information
output "security_info" {
  description = "Security configuration information"
  value = {
    encryption_at_rest = var.enable_encryption
    vpc_enabled       = true
    private_subnets   = length(module.vpc.private_subnet_ids)
    security_groups   = 2
    iam_roles         = 3
    s3_bucket_policy  = "Enabled"
    cloudtrail        = "Recommended for production"
  }
}

# Monitoring Information
output "monitoring_info" {
  description = "Monitoring and alerting configuration"
  value = {
    cloudwatch_dashboard = module.cloudwatch.dashboard_name
    sns_topic          = module.sns.topic_name
    alarms_count       = 4
    log_groups         = length(module.cloudwatch.log_groups)
    metrics_namespace  = "CryptoAnalytics"
  }
}

# Development Information
output "development_info" {
  description = "Development and deployment information"
  value = {
    environment        = var.environment
    region            = var.aws_region
    terraform_version = ">= 1.0.0"
    localstack_enabled = var.enable_localstack
    docker_compose    = "Available for local development"
    ci_cd_pipeline    = "GitHub Actions configured"
  }
} 