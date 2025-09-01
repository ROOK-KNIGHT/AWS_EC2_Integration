#!/bin/bash

# AWS EC2 Deployment Script for Charles Schwab API Integration
# This script deploys the CloudFormation stack and sets up the application

set -e  # Exit on any error

# Configuration
STACK_NAME="schwab-api-stack"
TEMPLATE_FILE="aws/cloudformation-template.yaml"
KEY_PAIR_NAME="schwab-api-keypair"
INSTANCE_TYPE="t3.small"
ENVIRONMENT="production"
REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check if AWS CLI is installed and configured
check_aws_cli() {
    print_status "Checking AWS CLI configuration..."
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS CLI is not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    print_success "AWS CLI is configured"
}

# Function to create EC2 key pair if it doesn't exist
create_key_pair() {
    print_status "Checking for EC2 key pair: $KEY_PAIR_NAME"
    
    if aws ec2 describe-key-pairs --key-names "$KEY_PAIR_NAME" --region "$REGION" &> /dev/null; then
        print_success "Key pair $KEY_PAIR_NAME already exists"
    else
        print_status "Creating EC2 key pair: $KEY_PAIR_NAME"
        aws ec2 create-key-pair \
            --key-name "$KEY_PAIR_NAME" \
            --region "$REGION" \
            --query 'KeyMaterial' \
            --output text > "${KEY_PAIR_NAME}.pem"
        
        chmod 400 "${KEY_PAIR_NAME}.pem"
        print_success "Key pair created and saved as ${KEY_PAIR_NAME}.pem"
        print_warning "Keep this file safe! You'll need it to SSH into your EC2 instance."
    fi
}

# Function to deploy CloudFormation stack
deploy_stack() {
    print_status "Deploying CloudFormation stack: $STACK_NAME"
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &> /dev/null; then
        print_status "Stack exists, updating..."
        aws cloudformation update-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://"$TEMPLATE_FILE" \
            --parameters \
                ParameterKey=KeyPairName,ParameterValue="$KEY_PAIR_NAME" \
                ParameterKey=InstanceType,ParameterValue="$INSTANCE_TYPE" \
                ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$REGION"
        
        print_status "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete \
            --stack-name "$STACK_NAME" \
            --region "$REGION"
    else
        print_status "Creating new stack..."
        aws cloudformation create-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://"$TEMPLATE_FILE" \
            --parameters \
                ParameterKey=KeyPairName,ParameterValue="$KEY_PAIR_NAME" \
                ParameterKey=InstanceType,ParameterValue="$INSTANCE_TYPE" \
                ParameterKey=Environment,ParameterValue="$ENVIRONMENT" \
            --capabilities CAPABILITY_NAMED_IAM \
            --region "$REGION"
        
        print_status "Waiting for stack creation to complete..."
        aws cloudformation wait stack-create-complete \
            --stack-name "$STACK_NAME" \
            --region "$REGION"
    fi
    
    print_success "CloudFormation stack deployed successfully"
}

# Function to get stack outputs
get_stack_outputs() {
    print_status "Getting stack outputs..."
    
    INSTANCE_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`InstanceId`].OutputValue' \
        --output text)
    
    PUBLIC_IP=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`PublicIP`].OutputValue' \
        --output text)
    
    PUBLIC_DNS=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`PublicDNS`].OutputValue' \
        --output text)
    
    SECRET_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`SecretArn`].OutputValue' \
        --output text)
    
    echo ""
    print_success "Deployment completed successfully!"
    echo ""
    echo "=== DEPLOYMENT INFORMATION ==="
    echo "Instance ID: $INSTANCE_ID"
    echo "Public IP: $PUBLIC_IP"
    echo "Public DNS: $PUBLIC_DNS"
    echo "Secret ARN: $SECRET_ARN"
    echo ""
    echo "SSH Command:"
    echo "ssh -i ${KEY_PAIR_NAME}.pem ec2-user@${PUBLIC_IP}"
    echo ""
    echo "Next steps:"
    echo "1. Update the Secrets Manager secret with your actual Schwab API credentials"
    echo "2. SSH into the instance and deploy your application code"
    echo "3. Configure your application to use AWS Secrets Manager for credentials"
    echo ""
}

# Function to update secrets manager with actual credentials
update_secrets() {
    if [ -f ".env" ]; then
        print_status "Found .env file, updating Secrets Manager..."
        
        # Read values from .env file
        SCHWAB_APP_KEY=$(grep SCHWAB_APP_KEY .env | cut -d '=' -f2 | tr -d '"')
        SCHWAB_APP_SECRET=$(grep SCHWAB_APP_SECRET .env | cut -d '=' -f2 | tr -d '"')
        
        # Use the EC2 public IP for the callback URI
        CALLBACK_URI="https://${PUBLIC_IP}:8080/callback"
        
        if [ -n "$SCHWAB_APP_KEY" ] && [ -n "$SCHWAB_APP_SECRET" ]; then
            SECRET_VALUE=$(cat <<EOF
{
  "SCHWAB_APP_KEY": "$SCHWAB_APP_KEY",
  "SCHWAB_APP_SECRET": "$SCHWAB_APP_SECRET",
  "SCHWAB_REDIRECT_URI": "$CALLBACK_URI"
}
EOF
)
            
            aws secretsmanager update-secret \
                --secret-id "$SECRET_ARN" \
                --secret-string "$SECRET_VALUE" \
                --region "$REGION"
            
            print_success "Secrets Manager updated with your API credentials"
            print_success "Callback URI set to: $CALLBACK_URI"
        else
            print_warning "Could not find valid credentials in .env file"
        fi
    else
        print_warning ".env file not found. You'll need to manually update Secrets Manager."
    fi
}

# Main execution
main() {
    echo "=== AWS EC2 Deployment for Charles Schwab API Integration ==="
    echo ""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --stack-name)
                STACK_NAME="$2"
                shift 2
                ;;
            --key-pair)
                KEY_PAIR_NAME="$2"
                shift 2
                ;;
            --instance-type)
                INSTANCE_TYPE="$2"
                shift 2
                ;;
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --region)
                REGION="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --stack-name NAME       CloudFormation stack name (default: schwab-api-stack)"
                echo "  --key-pair NAME         EC2 key pair name (default: schwab-api-keypair)"
                echo "  --instance-type TYPE    EC2 instance type (default: t3.small)"
                echo "  --environment ENV       Environment name (default: production)"
                echo "  --region REGION         AWS region (default: us-east-1)"
                echo "  --help                  Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    print_status "Configuration:"
    echo "  Stack Name: $STACK_NAME"
    echo "  Key Pair: $KEY_PAIR_NAME"
    echo "  Instance Type: $INSTANCE_TYPE"
    echo "  Environment: $ENVIRONMENT"
    echo "  Region: $REGION"
    echo ""
    
    # Execute deployment steps
    check_aws_cli
    create_key_pair
    deploy_stack
    get_stack_outputs
    update_secrets
    
    print_success "Deployment process completed!"
}

# Run main function
main "$@"
