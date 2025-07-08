# Setup Guide

This guide provides step-by-step instructions for setting up the Crypto Analytics Dashboard in both local development and production environments.

## 📋 Prerequisites

### Required Software
- **Python**: 3.9 or higher
- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **Terraform**: 1.0 or higher
- **AWS CLI**: 2.0 or higher

### Required AWS Services
- **IAM**: Appropriate permissions for all services
- **S3**: For data storage and Terraform state
- **Kinesis**: For real-time data streaming
- **Lambda**: For stream processing
- **Redshift**: For data warehouse
- **Glue**: For ETL processing
- **CloudWatch**: For monitoring and alerting
- **SNS**: For notifications

## 🚀 Quick Start (5 minutes)

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/crypto-analytics-dashboard.git
cd crypto-analytics-dashboard
```

### 2. Set Up Environment
```bash
# Copy environment template
cp env.example .env

# Edit with your AWS credentials
nano .env
```

### 3. Start Local Development
```bash
# Start all services
docker-compose up -d

# Check services
docker-compose ps
```

### 4. Run Tests
```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Run tests
python -m pytest tests/ -v
```

## 🏠 Local Development Setup

### 1. Environment Configuration

Create your `.env` file with the following variables:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Local Development
ENVIRONMENT=development
DEBUG=true
LOCALSTACK_ENDPOINT=http://localhost:4566

# Database
DATABASE_URL=postgresql://admin:password@localhost:5432/crypto_analytics

# Redis
REDIS_URL=redis://localhost:6379
```

### 2. Start LocalStack Services

```bash
# Start LocalStack
docker-compose up localstack -d

# Wait for services to be ready
sleep 30

# Create local AWS resources
python scripts/setup_localstack.py
```

### 3. Initialize Database

```bash
# Start PostgreSQL
docker-compose up postgres -d

# Wait for database to be ready
sleep 10

# Run database migrations
python scripts/init_database.py
```

### 4. Start Data Ingestion

```bash
# Start the producer
docker-compose up producer -d

# Check logs
docker-compose logs -f producer
```

### 5. Start Lambda Function

```bash
# Start Lambda container
docker-compose up lambda -d

# Check Lambda logs
docker-compose logs -f lambda
```

### 6. Access Services

- **Jupyter Notebook**: http://localhost:8888
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **LocalStack**: http://localhost:4566

## 🏭 Production Deployment

### 1. AWS Account Setup

#### Create IAM User
```bash
# Create IAM user for Terraform
aws iam create-user --user-name crypto-analytics-terraform

# Attach policies
aws iam attach-user-policy \
  --user-name crypto-analytics-terraform \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

#### Configure AWS CLI
```bash
aws configure
# Enter your access key, secret key, region
```

### 2. S3 Backend Setup

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://crypto-analytics-terraform-state

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket crypto-analytics-terraform-state \
  --versioning-configuration Status=Enabled
```

### 3. Infrastructure Deployment

#### Initialize Terraform
```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Validate configuration
terraform validate
```

#### Deploy Infrastructure
```bash
# Plan deployment
terraform plan -var-file=production.tfvars

# Apply changes
terraform apply -var-file=production.tfvars
```

### 4. Lambda Function Deployment

```bash
# Build Lambda package
cd src/lambda/stream_processor
zip -r ../../../dist/lambda-function.zip .

# Deploy to AWS
aws lambda update-function-code \
  --function-name crypto-stream-processor \
  --zip-file fileb://dist/lambda-function.zip
```

### 5. Start Data Ingestion

```bash
# Set production environment
export ENVIRONMENT=production

# Start the producer
python src/ingestion/producers/kinesis_producer.py
```

### 6. Verify Deployment

```bash
# Run health checks
python scripts/health_check.py --environment production

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace CryptoAnalytics \
  --metric-name RecordsProcessed \
  --start-time $(date -d '1 hour ago' --iso-8601) \
  --end-time $(date --iso-8601) \
  --period 300 \
  --statistics Sum
```

## 🔧 Configuration

### Environment Variables

#### AWS Configuration
```bash
AWS_REGION=us-east-1
AWS_PROFILE=default
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

#### Kinesis Configuration
```bash
KINESIS_STREAM_NAME=crypto-market-data
KINESIS_SHARD_COUNT=10
KINESIS_BATCH_SIZE=500
KINESIS_MAX_RETRIES=3
```

#### Lambda Configuration
```bash
LAMBDA_FUNCTION_NAME=crypto-stream-processor
LAMBDA_TIMEOUT=60
LAMBDA_MEMORY_SIZE=512
LAMBDA_RUNTIME=python3.9
```

#### S3 Configuration
```bash
S3_BUCKET_NAME=crypto-analytics-data
S3_RAW_DATA_PREFIX=raw/
S3_PROCESSED_DATA_PREFIX=processed/
```

#### Redshift Configuration
```bash
REDSHIFT_CLUSTER_ID=crypto-analytics
REDSHIFT_DATABASE=crypto_analytics
REDSHIFT_USERNAME=admin
REDSHIFT_PASSWORD=your_secure_password
```

### Terraform Variables

Create environment-specific variable files:

#### production.tfvars
```hcl
environment = "production"
aws_region = "us-east-1"

# Kinesis
kinesis_shard_count = 10
kinesis_retention_period = 24

# Lambda
lambda_timeout = 60
lambda_memory_size = 512

# Redshift
redshift_nodes = 2
redshift_node_type = "ra3.4xlarge"

# S3
s3_bucket_name = "crypto-analytics-data-prod"
```

#### staging.tfvars
```hcl
environment = "staging"
aws_region = "us-east-1"

# Kinesis
kinesis_shard_count = 5
kinesis_retention_period = 24

# Lambda
lambda_timeout = 60
lambda_memory_size = 256

# Redshift
redshift_nodes = 1
redshift_node_type = "ra3.xlplus"

# S3
s3_bucket_name = "crypto-analytics-data-staging"
```

## 🧪 Testing

### Unit Tests
```bash
# Run all unit tests
python -m pytest tests/unit/ -v

# Run with coverage
python -m pytest tests/unit/ --cov=src --cov-report=html
```

### Integration Tests
```bash
# Run integration tests
python -m pytest tests/integration/ -v

# Run with database
DATABASE_URL=postgresql://admin:password@localhost:5432/crypto_analytics \
  python -m pytest tests/integration/ -v
```

### Load Tests
```bash
# Run load tests
python -m pytest tests/load/ -v

# Run performance benchmarks
python scripts/performance_benchmark.py
```

### Security Tests
```bash
# Run security scan
bandit -r src/

# Run vulnerability scan
trivy fs .
```

## 🔍 Troubleshooting

### Common Issues

#### LocalStack Not Starting
```bash
# Check Docker resources
docker system prune -f

# Restart LocalStack
docker-compose down
docker-compose up localstack -d
```

#### Database Connection Issues
```bash
# Check PostgreSQL logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

#### Lambda Function Errors
```bash
# Check Lambda logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/crypto

# Test Lambda locally
docker-compose up lambda
```

#### Kinesis Stream Issues
```bash
# Check stream status
aws kinesis describe-stream --stream-name crypto-market-data

# Check shard metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kinesis \
  --metric-name GetRecords.IteratorAgeMilliseconds \
  --dimensions Name=StreamName,Value=crypto-market-data
```

### Performance Issues

#### High Lambda Duration
- Increase memory allocation
- Optimize code for cold starts
- Use connection pooling

#### Kinesis Iterator Age
- Increase Lambda concurrency
- Add more shards
- Optimize batch processing

#### Redshift Query Performance
- Run VACUUM and ANALYZE
- Check distribution keys
- Optimize sort keys

## 📊 Monitoring Setup

### CloudWatch Dashboards

#### System Health Dashboard
- Lambda error rates and duration
- Kinesis iterator age
- S3 storage metrics
- Redshift CPU and memory

#### Performance Dashboard
- Records processed per minute
- Processing latency
- Data quality scores
- Cost metrics

### Alerts

#### Critical Alerts
- Lambda function errors
- Kinesis iterator age > 5 minutes
- Redshift CPU > 80%
- Data quality score < 0.8

#### Warning Alerts
- Lambda duration > 30 seconds
- S3 storage > 80%
- Cost threshold exceeded
- Low throughput

## 🔒 Security Setup

### IAM Roles and Policies

#### Lambda Execution Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kinesis:GetRecords",
        "kinesis:GetShardIterator",
        "s3:PutObject",
        "s3:GetObject",
        "cloudwatch:PutMetricData",
        "sns:Publish"
      ],
      "Resource": "*"
    }
  ]
}
```

#### Glue Service Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "redshift:DescribeClusters",
        "redshift-data:ExecuteStatement"
      ],
      "Resource": "*"
    }
  ]
}
```

### Network Security

#### VPC Configuration
- Private subnets for Lambda and Redshift
- Public subnets for NAT Gateway
- Security groups with least privilege
- Network ACLs for additional filtering

#### Encryption
- S3: Server-side encryption with KMS
- Redshift: Encryption at rest
- Kinesis: Encryption in transit
- Lambda: Environment variable encryption

## 📈 Scaling

### Horizontal Scaling
- Increase Kinesis shards for higher throughput
- Add Lambda concurrent executions
- Scale Redshift nodes for query performance
- Use Glue auto-scaling

### Vertical Scaling
- Increase Lambda memory for faster execution
- Upgrade Redshift node types
- Optimize S3 storage classes
- Use provisioned concurrency for Lambda

## 🗑️ Cleanup

### Local Development
```bash
# Stop all services
docker-compose down

# Remove volumes
docker-compose down -v

# Clean up images
docker system prune -f
```

### Production Environment
```bash
# Destroy infrastructure
cd infrastructure/terraform
terraform destroy -var-file=production.tfvars

# Clean up S3 buckets
aws s3 rb s3://crypto-analytics-data --force
aws s3 rb s3://crypto-analytics-terraform-state --force
```

## 📞 Support

### Getting Help
- **Documentation**: Check this guide and other docs
- **Issues**: Create GitHub issues for bugs
- **Discussions**: Use GitHub Discussions for questions
- **Monitoring**: Check CloudWatch for system health

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

This setup guide provides everything needed to get the Crypto Analytics Dashboard running in both development and production environments. 