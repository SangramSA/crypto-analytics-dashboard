# Crypto Analytics Dashboard - Terraform Infrastructure
# This configuration provisions all AWS resources needed for the crypto analytics platform

terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "crypto-analytics-terraform-state"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "crypto-analytics-dashboard"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"
  
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
  azs         = var.availability_zones
  
  public_subnets  = var.public_subnet_cidrs
  private_subnets = var.private_subnet_cidrs
  
  enable_nat_gateway = var.environment == "production"
  single_nat_gateway = var.environment != "production"
}

# S3 Data Lake
module "s3" {
  source = "./modules/s3"
  
  environment = var.environment
  bucket_name = var.s3_bucket_name
  
  # Lifecycle policies
  lifecycle_rules = [
    {
      id      = "raw_data_lifecycle"
      prefix  = "raw/"
      enabled = true
      
      transition = [
        {
          days          = 90
          storage_class = "GLACIER"
        },
        {
          days          = 365
          storage_class = "DEEP_ARCHIVE"
        }
      ]
    },
    {
      id      = "processed_data_lifecycle"
      prefix  = "processed/"
      enabled = true
      
      transition = [
        {
          days          = 180
          storage_class = "GLACIER"
        }
      ]
    }
  ]
}

# Kinesis Data Streams
module "kinesis" {
  source = "./modules/kinesis"
  
  environment      = var.environment
  stream_name      = var.kinesis_stream_name
  shard_count      = var.kinesis_shard_count
  retention_period = var.kinesis_retention_period
  
  # Auto-scaling configuration
  enable_auto_scaling = var.environment == "production"
  min_shard_count     = var.kinesis_min_shards
  max_shard_count     = var.kinesis_max_shards
}

# Lambda Functions
module "lambda" {
  source = "./modules/lambda"
  
  environment = var.environment
  
  # Stream processor function
  function_name = var.lambda_function_name
  runtime       = var.lambda_runtime
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size
  
  # Environment variables
  environment_variables = {
    S3_BUCKET_NAME              = module.s3.bucket_name
    S3_RAW_DATA_PREFIX          = "raw/"
    S3_PROCESSED_DATA_PREFIX    = "processed/"
    DATA_QUALITY_THRESHOLD      = "0.8"
    PRICE_VALIDATION_MIN        = "0.01"
    PRICE_VALIDATION_MAX        = "1000000.0"
    VOLUME_VALIDATION_MIN       = "0.0"
    TIMESTAMP_TOLERANCE_SECONDS = "300"
    CLOUDWATCH_METRIC_NAMESPACE = "CryptoAnalytics"
    SNS_TOPIC_ARN              = module.sns.topic_arn
  }
  
  # VPC configuration
  vpc_config = {
    subnet_ids         = module.vpc.private_subnet_ids
    security_group_ids = [module.security_groups.lambda_security_group_id]
  }
  
  # Kinesis trigger
  kinesis_stream_arn = module.kinesis.stream_arn
  batch_size         = var.lambda_batch_size
  starting_position  = "LATEST"
}

# Redshift Cluster
module "redshift" {
  source = "./modules/redshift"
  
  environment = var.environment
  
  cluster_identifier = var.redshift_cluster_id
  database_name      = var.redshift_database
  master_username    = var.redshift_username
  master_password    = var.redshift_password
  
  node_type = var.redshift_node_type
  nodes     = var.redshift_nodes
  
  # VPC configuration
  vpc_security_group_ids = [module.security_groups.redshift_security_group_id]
  subnet_group_name      = module.redshift_subnet_group.subnet_group_name
  
  # Maintenance window
  maintenance_window = "sun:05:00-sun:06:00"
  
  # Snapshot configuration
  snapshot_identifier = var.redshift_snapshot_identifier
  skip_final_snapshot = var.environment != "production"
  
  # Parameter group
  parameter_group_name = module.redshift_parameter_group.parameter_group_name
}

# Redshift Subnet Group
module "redshift_subnet_group" {
  source = "./modules/redshift_subnet_group"
  
  name        = "${var.environment}-redshift-subnet-group"
  description = "Subnet group for Redshift cluster"
  subnet_ids  = module.vpc.private_subnet_ids
}

# Redshift Parameter Group
module "redshift_parameter_group" {
  source = "./modules/redshift_parameter_group"
  
  name        = "${var.environment}-redshift-params"
  description = "Parameter group for crypto analytics"
  family      = "redshift-1.0"
  
  parameters = [
    {
      name  = "max_connections"
      value = "150"
    },
    {
      name  = "wlm_json_configuration"
      value = jsonencode({
        wlm_config = [
          {
            query_concurrency = 5
            memory_percent    = 60
            short_query_queue = true
          },
          {
            query_concurrency = 2
            memory_percent    = 40
            short_query_queue = false
          }
        ]
      })
    }
  ]
}

# Glue Catalog and Jobs
module "glue" {
  source = "./modules/glue"
  
  environment = var.environment
  
  # Database
  database_name = var.glue_database_name
  description   = "Glue catalog for crypto analytics"
  
  # Crawler
  crawler_name = var.glue_crawler_name
  role_arn     = module.iam.glue_role_arn
  
  # S3 targets
  s3_targets = [
    {
      path = "s3://${module.s3.bucket_name}/raw/"
    }
  ]
  
  # Schedule
  schedule = "cron(0 */6 * * ? *)"  # Every 6 hours
  
  # ETL Job
  job_name = var.glue_job_name
  role_arn = module.iam.glue_role_arn
  
  # Job parameters
  job_parameters = {
    "--s3_bucket"        = module.s3.bucket_name
    "--raw_prefix"       = "raw/"
    "--processed_prefix" = "processed/"
    "--redshift_cluster" = module.redshift.cluster_endpoint
    "--redshift_database" = var.redshift_database
    "--redshift_username" = var.redshift_username
    "--redshift_password" = var.redshift_password
  }
  
  # Job configuration
  worker_type = var.glue_worker_type
  num_workers = var.glue_num_workers
  timeout     = var.glue_timeout
}

# CloudWatch Monitoring
module "cloudwatch" {
  source = "./modules/cloudwatch"
  
  environment = var.environment
  
  # Dashboard
  dashboard_name = var.cloudwatch_dashboard_name
  
  # Alarms
  alarms = {
    lambda_errors = {
      name          = "${var.environment}-lambda-errors"
      description   = "Lambda function error rate"
      metric_name   = "Errors"
      namespace     = "AWS/Lambda"
      statistic     = "Sum"
      period        = 300
      evaluation_periods = 2
      threshold     = 1
      comparison_operator = "GreaterThanThreshold"
    },
    
    kinesis_iterator_age = {
      name          = "${var.environment}-kinesis-iterator-age"
      description   = "Kinesis iterator age"
      metric_name   = "IteratorAgeMilliseconds"
      namespace     = "AWS/Kinesis"
      statistic     = "Maximum"
      period        = 300
      evaluation_periods = 2
      threshold     = 60000  # 60 seconds
      comparison_operator = "GreaterThanThreshold"
    },
    
    redshift_cpu = {
      name          = "${var.environment}-redshift-cpu"
      description   = "Redshift CPU utilization"
      metric_name   = "CPUUtilization"
      namespace     = "AWS/Redshift"
      statistic     = "Average"
      period        = 300
      evaluation_periods = 2
      threshold     = 80
      comparison_operator = "GreaterThanThreshold"
    },
    
    data_quality = {
      name          = "${var.environment}-data-quality"
      description   = "Data quality score"
      metric_name   = "DataQualityScore"
      namespace     = "CryptoAnalytics"
      statistic     = "Average"
      period        = 300
      evaluation_periods = 2
      threshold     = 0.8
      comparison_operator = "LessThanThreshold"
    }
  }
  
  # SNS topic for alarms
  sns_topic_arn = module.sns.topic_arn
}

# SNS Topics
module "sns" {
  source = "./modules/sns"
  
  environment = var.environment
  
  # Main alerts topic
  topic_name = "${var.environment}-crypto-alerts"
  display_name = "Crypto Analytics Alerts"
  
  # Email subscriptions
  subscriptions = var.sns_email_subscriptions
}

# Security Groups
module "security_groups" {
  source = "./modules/security_groups"
  
  environment = var.environment
  vpc_id      = module.vpc.vpc_id
  
  # Lambda security group
  lambda_security_group = {
    name        = "${var.environment}-lambda-sg"
    description = "Security group for Lambda functions"
    rules = [
      {
        type        = "egress"
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
      }
    ]
  }
  
  # Redshift security group
  redshift_security_group = {
    name        = "${var.environment}-redshift-sg"
    description = "Security group for Redshift cluster"
    rules = [
      {
        type        = "ingress"
        from_port   = 5439
        to_port     = 5439
        protocol    = "tcp"
        cidr_blocks = [var.vpc_cidr]
      },
      {
        type        = "egress"
        from_port   = 0
        to_port     = 0
        protocol    = "-1"
        cidr_blocks = ["0.0.0.0/0"]
      }
    ]
  }
}

# IAM Roles and Policies
module "iam" {
  source = "./modules/iam"
  
  environment = var.environment
  
  # Lambda role
  lambda_role = {
    name = "${var.environment}-lambda-role"
    policies = [
      {
        name = "lambda-execution-policy"
        statements = [
          {
            Effect = "Allow"
            Action = [
              "logs:CreateLogGroup",
              "logs:CreateLogStream",
              "logs:PutLogEvents"
            ]
            Resource = "*"
          },
          {
            Effect = "Allow"
            Action = [
              "s3:GetObject",
              "s3:PutObject",
              "s3:DeleteObject"
            ]
            Resource = "${module.s3.bucket_arn}/*"
          },
          {
            Effect = "Allow"
            Action = [
              "cloudwatch:PutMetricData"
            ]
            Resource = "*"
          },
          {
            Effect = "Allow"
            Action = [
              "sns:Publish"
            ]
            Resource = module.sns.topic_arn
          }
        ]
      }
    ]
  }
  
  # Glue role
  glue_role = {
    name = "${var.environment}-glue-role"
    policies = [
      {
        name = "glue-execution-policy"
        statements = [
          {
            Effect = "Allow"
            Action = [
              "s3:GetObject",
              "s3:PutObject",
              "s3:DeleteObject"
            ]
            Resource = "${module.s3.bucket_arn}/*"
          },
          {
            Effect = "Allow"
            Action = [
              "redshift:DescribeClusters",
              "redshift:DescribeClusterParameters"
            ]
            Resource = "*"
          }
        ]
      }
    ]
  }
  
  # Redshift role
  redshift_role = {
    name = "${var.environment}-redshift-role"
    policies = [
      {
        name = "redshift-execution-policy"
        statements = [
          {
            Effect = "Allow"
            Action = [
              "s3:GetObject",
              "s3:PutObject"
            ]
            Resource = "${module.s3.bucket_arn}/*"
          }
        ]
      }
    ]
  }
}

# QuickSight Data Source
module "quicksight" {
  source = "./modules/quicksight"
  
  environment = var.environment
  
  # Data source
  datasource_name = "${var.environment}-crypto-datasource"
  datasource_type = "REDSHIFT"
  
  # Redshift connection
  redshift_cluster_id = module.redshift.cluster_id
  redshift_database   = var.redshift_database
  redshift_username   = var.redshift_username
  redshift_password   = var.redshift_password
  
  # Permissions
  principal_arn = var.quicksight_user_arn
}

# Outputs
output "kinesis_stream_arn" {
  description = "ARN of the Kinesis stream"
  value       = module.kinesis.stream_arn
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = module.lambda.function_arn
}

output "redshift_cluster_endpoint" {
  description = "Redshift cluster endpoint"
  value       = module.redshift.cluster_endpoint
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = module.s3.bucket_name
}

output "cloudwatch_dashboard_url" {
  description = "URL of the CloudWatch dashboard"
  value       = module.cloudwatch.dashboard_url
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic"
  value       = module.sns.topic_arn
} 