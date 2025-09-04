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
        print_success "Key pair $KEY_PAIR_NAME already exists in AWS"
        
        # Check if we have the local key file
        if [ ! -f "${KEY_PAIR_NAME}.pem" ]; then
            print_warning "Local key file ${KEY_PAIR_NAME}.pem not found"
            print_status "Creating new timestamped key pair for this deployment..."
            
            # Create a new key pair with timestamp
            TIMESTAMP=$(date +%Y%m%d-%H%M%S)
            NEW_KEY_PAIR_NAME="${KEY_PAIR_NAME}-${TIMESTAMP}"
            
            aws ec2 create-key-pair \
                --key-name "$NEW_KEY_PAIR_NAME" \
                --region "$REGION" \
                --query 'KeyMaterial' \
                --output text > "${NEW_KEY_PAIR_NAME}.pem"
            
            chmod 400 "${NEW_KEY_PAIR_NAME}.pem"
            
            # Update the key pair name for this deployment
            KEY_PAIR_NAME="$NEW_KEY_PAIR_NAME"
            
            print_success "New key pair created: ${KEY_PAIR_NAME}.pem"
            print_warning "Keep this file safe! You'll need it to SSH into your EC2 instance."
        else
            print_success "Local key file ${KEY_PAIR_NAME}.pem found"
        fi
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
    print_status "Using key pair: $KEY_PAIR_NAME"
    
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

# Function to check if SSH key file exists locally
check_ssh_key() {
    if [ ! -f "${KEY_PAIR_NAME}.pem" ]; then
        print_error "SSH key file ${KEY_PAIR_NAME}.pem not found!"
        print_error "This key should have been created during the key pair creation step."
        exit 1
    fi
    
    # Ensure correct permissions
    chmod 400 "${KEY_PAIR_NAME}.pem"
}

# Function to wait for EC2 instance to be ready
wait_for_instance() {
    print_status "Waiting for EC2 instance to be ready..."
    
    # Wait for instance to be running
    aws ec2 wait instance-running --instance-ids "$INSTANCE_ID" --region "$REGION"
    
    # Wait for SSH to be available (retry for up to 5 minutes)
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if ssh -i "${KEY_PAIR_NAME}.pem" -o ConnectTimeout=10 -o StrictHostKeyChecking=no ec2-user@"$PUBLIC_IP" "echo 'SSH ready'" &> /dev/null; then
            print_success "EC2 instance is ready for SSH connections"
            return 0
        fi
        
        print_status "Waiting for SSH to be available... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    print_error "EC2 instance is not responding to SSH after 5 minutes"
    exit 1
}

# Function to deploy application code to EC2
deploy_application() {
    print_status "Deploying application code to EC2 instance..."
    
    # Create application directory
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$PUBLIC_IP" "sudo mkdir -p /opt/schwab-api && sudo chown ec2-user:ec2-user /opt/schwab-api"
    
    # Create necessary subdirectories
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$PUBLIC_IP" "mkdir -p /opt/schwab-api/{logs,data,tokens,handlers}"
    
    # Upload application files
    print_status "Uploading application files..."
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no app.py requirements.txt ec2-user@"$PUBLIC_IP":/opt/schwab-api/
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no handlers/*.py ec2-user@"$PUBLIC_IP":/opt/schwab-api/handlers/
    
    print_success "Application files uploaded"
    
    # Install Python dependencies
    print_status "Installing Python dependencies..."
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$PUBLIC_IP" "cd /opt/schwab-api && python3 -m pip install --user -r requirements.txt"
    print_success "Dependencies installed"
    
    # Create systemd service file
    print_status "Creating systemd service..."
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$PUBLIC_IP" "sudo tee /etc/systemd/system/schwab-api.service > /dev/null << 'EOF'
[Unit]
Description=Charles Schwab API Integration
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/schwab-api
Environment=PATH=/home/ec2-user/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 /opt/schwab-api/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"
    
    # Reload systemd and start service
    print_status "Starting application service..."
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$PUBLIC_IP" "
        sudo systemctl daemon-reload
        sudo systemctl enable schwab-api
        sudo systemctl start schwab-api
    "
    
    # Wait a moment for service to start
    sleep 10
    
    # Check service status
    if ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$PUBLIC_IP" "sudo systemctl is-active --quiet schwab-api"; then
        print_success "Application service is running"
    else
        print_error "Application service failed to start"
        print_status "Checking service logs..."
        ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$PUBLIC_IP" "sudo journalctl -u schwab-api --no-pager -n 20"
        exit 1
    fi
}

# Function to verify application is working
verify_application() {
    print_status "Verifying application deployment..."
    
    # Wait a bit more for the application to fully start
    sleep 15
    
    # Test application health endpoint
    local max_attempts=6
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://$PUBLIC_IP:8080/health" > /dev/null; then
            print_success "Application health check passed"
            
            # Test the auth endpoint to make sure secrets are loaded
            if curl -f -s "http://$PUBLIC_IP:8080/api/auth/start" > /dev/null; then
                print_success "Application is fully functional"
                return 0
            else
                print_warning "Application is running but authentication endpoint may have issues"
                return 0
            fi
        fi
        
        print_status "Waiting for application to be ready... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    print_warning "Application health check failed, but deployment completed"
    print_status "You may need to check the application logs manually"
}

# Function to display final deployment information
show_deployment_info() {
    echo ""
    echo "=================================================================="
    print_success "DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "=================================================================="
    echo ""
    echo "🌐 Application URL: http://$PUBLIC_IP:8080"
    echo ""
    echo "📋 Instance Information:"
    echo "   Instance ID: $INSTANCE_ID"
    echo "   Public IP: $PUBLIC_IP"
    echo "   Public DNS: $PUBLIC_DNS"
    echo ""
    echo "🔑 SSH Access:"
    echo "   ssh -i ${KEY_PAIR_NAME}.pem ec2-user@$PUBLIC_IP"
    echo ""
    echo "🔧 Service Management:"
    echo "   Check status: sudo systemctl status schwab-api"
    echo "   View logs: sudo journalctl -u schwab-api -f"
    echo "   Restart: sudo systemctl restart schwab-api"
    echo ""
    echo "🚀 Next Steps:"
    echo "   1. Open http://$PUBLIC_IP:8080 in your browser"
    echo "   2. Click 'Authenticate with Charles Schwab'"
    echo "   3. Complete the OAuth flow to start trading"
    echo ""
    echo "📚 The application includes:"
    echo "   • Charles Schwab OAuth authentication"
    echo "   • Account positions viewing"
    echo "   • Historical data retrieval"
    echo "   • Order placement interface"
    echo "   • Automatic token management"
    echo ""
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
    check_ssh_key
    wait_for_instance
    deploy_application
    verify_application
    show_deployment_info
}

# Run main function
main "$@"
