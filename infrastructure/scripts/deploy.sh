#!/bin/bash

# Crypto Analytics Dashboard - Deployment Script
# This script automates the deployment of the crypto analytics platform

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform"
LAMBDA_DIR="$PROJECT_ROOT/src/lambda/stream_processor"

# Default values
ENVIRONMENT="dev"
REGION="us-east-1"
ACTION="deploy"
DRY_RUN=false
SKIP_TESTS=false

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] ACTION

Actions:
    deploy      Deploy the entire infrastructure and application
    destroy     Destroy the infrastructure (use with caution)
    update      Update existing infrastructure
    validate    Validate Terraform configuration
    test        Run tests only
    monitor     Show monitoring information

Options:
    -e, --environment ENV    Environment (dev, staging, production) [default: dev]
    -r, --region REGION     AWS region [default: us-east-1]
    -d, --dry-run          Show what would be deployed without actually deploying
    -s, --skip-tests       Skip running tests before deployment
    -h, --help             Show this help message

Examples:
    $0 deploy                    # Deploy to dev environment
    $0 -e production deploy     # Deploy to production
    $0 -d deploy               # Dry run deployment
    $0 validate                 # Validate configuration
    $0 monitor                  # Show monitoring info

EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if required tools are installed
    local missing_tools=()
    
    if ! command -v terraform &> /dev/null; then
        missing_tools+=("terraform")
    fi
    
    if ! command -v aws &> /dev/null; then
        missing_tools+=("aws")
    fi
    
    if ! command -v python3 &> /dev/null; then
        missing_tools+=("python3")
    fi
    
    if ! command -v pip3 &> /dev/null; then
        missing_tools+=("pip3")
    fi
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_error "Please install the missing tools and try again."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Check Python dependencies
    if ! python3 -c "import boto3, structlog" &> /dev/null; then
        print_warning "Python dependencies not installed. Installing now..."
        pip3 install -r "$PROJECT_ROOT/requirements.txt"
    fi
    
    print_success "Prerequisites check completed"
}

# Function to validate Terraform configuration
validate_terraform() {
    print_status "Validating Terraform configuration..."
    
    cd "$TERRAFORM_DIR"
    
    if ! terraform init; then
        print_error "Terraform initialization failed"
        exit 1
    fi
    
    if ! terraform validate; then
        print_error "Terraform validation failed"
        exit 1
    fi
    
    if ! terraform fmt -check; then
        print_warning "Terraform files need formatting. Run 'terraform fmt' to fix."
    fi
    
    print_success "Terraform validation completed"
}

# Function to run tests
run_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        print_warning "Skipping tests as requested"
        return 0
    fi
    
    print_status "Running tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run unit tests
    if ! python3 -m pytest tests/unit/ -v --cov=src --cov-report=term-missing; then
        print_error "Unit tests failed"
        exit 1
    fi
    
    # Run integration tests if not dry run
    if [ "$DRY_RUN" = false ]; then
        if ! python3 -m pytest tests/integration/ -v; then
            print_error "Integration tests failed"
            exit 1
        fi
    fi
    
    print_success "Tests completed successfully"
}

# Function to build Lambda package
build_lambda_package() {
    print_status "Building Lambda package..."
    
    cd "$LAMBDA_DIR"
    
    # Create deployment package
    rm -rf dist/
    mkdir -p dist/
    
    # Install dependencies
    pip3 install -r requirements.txt -t dist/
    
    # Copy Lambda function code
    cp handler.py dist/
    
    # Create ZIP file
    cd dist/
    zip -r ../lambda-function.zip .
    cd ..
    
    print_success "Lambda package built successfully"
}

# Function to deploy infrastructure
deploy_infrastructure() {
    print_status "Deploying infrastructure..."
    
    cd "$TERRAFORM_DIR"
    
    # Set Terraform variables
    export TF_VAR_environment="$ENVIRONMENT"
    export TF_VAR_aws_region="$REGION"
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    if [ "$DRY_RUN" = true ]; then
        print_status "Dry run - showing deployment plan..."
        terraform plan -var-file="${ENVIRONMENT}.tfvars"
        return 0
    fi
    
    # Apply Terraform configuration
    if ! terraform apply -var-file="${ENVIRONMENT}.tfvars" -auto-approve; then
        print_error "Infrastructure deployment failed"
        exit 1
    fi
    
    # Get outputs
    terraform output -json > outputs.json
    
    print_success "Infrastructure deployed successfully"
}

# Function to deploy Lambda function
deploy_lambda() {
    print_status "Deploying Lambda function..."
    
    # Get Lambda function name from Terraform output
    local function_name
    function_name=$(cd "$TERRAFORM_DIR" && terraform output -raw lambda_function_name 2>/dev/null || echo "${ENVIRONMENT}-crypto-stream-processor")
    
    # Update Lambda function code
    if ! aws lambda update-function-code \
        --function-name "$function_name" \
        --zip-file fileb://"$LAMBDA_DIR/lambda-function.zip" \
        --region "$REGION"; then
        print_error "Lambda function deployment failed"
        exit 1
    fi
    
    print_success "Lambda function deployed successfully"
}

# Function to run health checks
run_health_checks() {
    print_status "Running health checks..."
    
    cd "$PROJECT_ROOT"
    
    # Run health check script
    if [ -f "scripts/health_check.py" ]; then
        if ! python3 scripts/health_check.py --environment "$ENVIRONMENT"; then
            print_warning "Health checks failed"
        else
            print_success "Health checks passed"
        fi
    fi
}

# Function to show monitoring information
show_monitoring() {
    print_status "Showing monitoring information..."
    
    cd "$TERRAFORM_DIR"
    
    # Get CloudWatch dashboard URL
    local dashboard_url
    dashboard_url=$(terraform output -raw cloudwatch_dashboard_url 2>/dev/null || echo "Dashboard not available")
    
    print_status "CloudWatch Dashboard: $dashboard_url"
    
    # Get other important URLs
    local region="$REGION"
    local environment="$ENVIRONMENT"
    
    cat << EOF

Monitoring URLs:
- CloudWatch Dashboard: $dashboard_url
- Lambda Console: https://console.aws.amazon.com/lambda/home?region=$region#/functions/$environment-crypto-stream-processor
- Kinesis Console: https://console.aws.amazon.com/kinesis/home?region=$region#/streams/details/$environment-crypto-market-data
- S3 Console: https://console.aws.amazon.com/s3/buckets/$environment-crypto-analytics-data?region=$region
- Redshift Console: https://console.aws.amazon.com/redshift/home?region=$region

EOF
}

# Function to destroy infrastructure
destroy_infrastructure() {
    print_warning "This will destroy all infrastructure. Are you sure? (y/N)"
    read -r response
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Destroying infrastructure..."
        
        cd "$TERRAFORM_DIR"
        
        # Set Terraform variables
        export TF_VAR_environment="$ENVIRONMENT"
        export TF_VAR_aws_region="$REGION"
        
        # Initialize Terraform
        terraform init
        
        # Destroy infrastructure
        if ! terraform destroy -var-file="${ENVIRONMENT}.tfvars" -auto-approve; then
            print_error "Infrastructure destruction failed"
            exit 1
        fi
        
        print_success "Infrastructure destroyed successfully"
    else
        print_status "Destruction cancelled"
    fi
}

# Function to create environment-specific tfvars file
create_tfvars() {
    local env_file="$TERRAFORM_DIR/${ENVIRONMENT}.tfvars"
    
    if [ ! -f "$env_file" ]; then
        print_status "Creating ${ENVIRONMENT}.tfvars file..."
        
        cat > "$env_file" << EOF
# ${ENVIRONMENT} environment configuration
environment = "${ENVIRONMENT}"
aws_region = "${REGION}"

# Redshift configuration
redshift_password = "your_secure_password_here"

# SNS subscriptions
sns_email_subscriptions = ["your-email@example.com"]

# QuickSight user ARN (optional)
quicksight_user_arn = ""

# Performance configuration
enable_auto_scaling = ${ENVIRONMENT == "production" ? "true" : "false"}
enable_monitoring = true
enable_backup = true

# Cost optimization
enable_spot_instances = false
enable_schedule_pause = ${ENVIRONMENT != "production" ? "true" : "false"}

EOF
        
        print_warning "Please edit $env_file with your specific configuration before deploying"
    fi
}

# Main function
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -r|--region)
                REGION="$2"
                shift 2
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -s|--skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            deploy|destroy|update|validate|test|monitor)
                ACTION="$1"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
        print_error "Invalid environment: $ENVIRONMENT"
        exit 1
    fi
    
    # Show deployment information
    print_status "Deployment Configuration:"
    print_status "  Environment: $ENVIRONMENT"
    print_status "  Region: $REGION"
    print_status "  Action: $ACTION"
    print_status "  Dry Run: $DRY_RUN"
    print_status "  Skip Tests: $SKIP_TESTS"
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Create tfvars file if it doesn't exist
    create_tfvars
    
    # Execute action
    case $ACTION in
        deploy)
            validate_terraform
            run_tests
            build_lambda_package
            deploy_infrastructure
            deploy_lambda
            run_health_checks
            show_monitoring
            print_success "Deployment completed successfully!"
            ;;
        destroy)
            destroy_infrastructure
            ;;
        update)
            validate_terraform
            run_tests
            build_lambda_package
            deploy_infrastructure
            deploy_lambda
            run_health_checks
            print_success "Update completed successfully!"
            ;;
        validate)
            validate_terraform
            ;;
        test)
            run_tests
            ;;
        monitor)
            show_monitoring
            ;;
        *)
            print_error "Unknown action: $ACTION"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 