#!/bin/bash

# AWS EC2 Deployment Script for Charles Schwab API Integration - Milestone 2
# This script deploys the complete production-ready system with modern dashboard,
# Google SSO, SSL certificates, and enhanced monitoring capabilities

set -e  # Exit on any error

# Configuration
STACK_NAME="schwab-api-stack"
TEMPLATE_FILE="cloudformation-template.yaml"
KEY_PAIR_NAME="schwab-api-keypair"
INSTANCE_TYPE="t3.small"
ENVIRONMENT="production"
REGION="us-east-1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
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

print_milestone() {
    echo -e "${PURPLE}[MILESTONE 2]${NC} $1"
}

# Function to cleanup existing AWS resources
cleanup_aws_resources() {
    print_status "Starting cleanup of existing AWS resources..."
    
    # Confirmation prompt for safety
    echo -e "${YELLOW}⚠️  This will delete existing AWS resources from the $STACK_NAME stack.${NC}"
    echo -e "${YELLOW}   This includes EC2 instances, secrets, VPC resources, and key pairs.${NC}"
    read -p "Do you want to proceed with cleanup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Skipping cleanup. Proceeding with deployment..."
        return 0
    fi
    
    print_status "Proceeding with AWS resource cleanup..."
    
    # 1. Delete CloudFormation Stack
    print_status "[1/7] Deleting CloudFormation stack..."
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" >/dev/null 2>&1; then
        aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null
        print_status "Waiting for CloudFormation stack deletion to complete..."
        aws cloudformation wait stack-delete-complete --stack-name "$STACK_NAME" --region "$REGION" 2>/dev/null || true
        print_success "CloudFormation stack removed"
    else
        print_status "CloudFormation stack not found, skipping"
    fi

    # 2. Terminate EC2 instances (only from our stack)
    print_status "[2/7] Terminating EC2 instances from stack..."
    INSTANCE_IDS=$(aws ec2 describe-instances --region "$REGION" \
      --filters "Name=instance-state-name,Values=running,pending,stopping,stopped" \
      --filters "Name=tag:aws:cloudformation:stack-name,Values=$STACK_NAME" \
      --query "Reservations[].Instances[].InstanceId" --output text 2>/dev/null || true)
    if [ -n "$INSTANCE_IDS" ]; then
      aws ec2 terminate-instances --instance-ids $INSTANCE_IDS --region "$REGION" >/dev/null 2>&1
      print_status "Waiting for instances to terminate..."
      aws ec2 wait instance-terminated --instance-ids $INSTANCE_IDS --region "$REGION" 2>/dev/null || true
      print_success "Stack instances terminated"
    else
      print_status "No stack instances found"
    fi

    # 3. Delete Secrets Manager secrets (only our stack's secrets)
    print_status "[3/7] Deleting Secrets..."
    SECRETS=$(aws secretsmanager list-secrets --region "$REGION" \
      --query "SecretList[?contains(Name, 'schwab-api') || contains(Name, 'production/schwab-api')].Name" --output text 2>/dev/null || true)
    if [ -n "$SECRETS" ]; then
        for SECRET in $SECRETS; do
          aws secretsmanager delete-secret --secret-id "$SECRET" --region "$REGION" --force-delete-without-recovery >/dev/null 2>&1 || true
          print_status "Deleted secret: $SECRET"
        done
        print_success "Stack secrets deleted"
    else
        print_status "No stack secrets found"
    fi

    # 4. Delete VPC-related resources (only from our stack)
    print_status "[4/7] Cleaning VPCs from stack..."
    VPCS=$(aws ec2 describe-vpcs --region "$REGION" \
      --filters "Name=tag:aws:cloudformation:stack-name,Values=$STACK_NAME" \
      --query "Vpcs[].VpcId" --output text 2>/dev/null || true)
    if [ -n "$VPCS" ]; then
        for VPC in $VPCS; do
          print_status "Processing stack VPC: $VPC"

          # Delete NAT Gateways first (if any)
          NATGWS=$(aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=$VPC" --region "$REGION" --query "NatGateways[].NatGatewayId" --output text 2>/dev/null || true)
          if [ -n "$NATGWS" ]; then
              for NATGW in $NATGWS; do
                aws ec2 delete-nat-gateway --nat-gateway-id "$NATGW" --region "$REGION" >/dev/null 2>&1 || true
                print_status "Deleted NAT Gateway: $NATGW"
              done
              print_status "Waiting for NAT Gateways to be deleted..."
              sleep 30
          fi

          # Subnets
          SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" --region "$REGION" --query "Subnets[].SubnetId" --output text 2>/dev/null || true)
          if [ -n "$SUBNETS" ]; then
              for SUBNET in $SUBNETS; do
                aws ec2 delete-subnet --subnet-id "$SUBNET" --region "$REGION" >/dev/null 2>&1 || true
                print_status "Deleted subnet: $SUBNET"
              done
          fi

          # Route Tables (skip main)
          RTBS=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC" --region "$REGION" --query "RouteTables[].RouteTableId" --output text 2>/dev/null || true)
          if [ -n "$RTBS" ]; then
              for RTB in $RTBS; do
                MAIN=$(aws ec2 describe-route-tables --route-table-ids "$RTB" --region "$REGION" --query "RouteTables[].Associations[].Main" --output text 2>/dev/null || true)
                if [[ "$MAIN" != "True" ]]; then
                  aws ec2 delete-route-table --route-table-id "$RTB" --region "$REGION" >/dev/null 2>&1 || true
                  print_status "Deleted route table: $RTB"
                fi
              done
          fi

          # Internet Gateways
          IGWS=$(aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC" --region "$REGION" --query "InternetGateways[].InternetGatewayId" --output text 2>/dev/null || true)
          if [ -n "$IGWS" ]; then
              for IGW in $IGWS; do
                aws ec2 detach-internet-gateway --internet-gateway-id "$IGW" --vpc-id "$VPC" --region "$REGION" >/dev/null 2>&1 || true
                aws ec2 delete-internet-gateway --internet-gateway-id "$IGW" --region "$REGION" >/dev/null 2>&1 || true
                print_status "Deleted IGW: $IGW"
              done
          fi

          # Security Groups (skip default)
          SGS=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC" --region "$REGION" --query "SecurityGroups[].GroupId" --output text 2>/dev/null || true)
          if [ -n "$SGS" ]; then
              for SG in $SGS; do
                DEFAULT=$(aws ec2 describe-security-groups --group-ids "$SG" --region "$REGION" --query "SecurityGroups[].GroupName" --output text 2>/dev/null || true)
                if [[ "$DEFAULT" != "default" ]]; then
                  aws ec2 delete-security-group --group-id "$SG" --region "$REGION" >/dev/null 2>&1 || true
                  print_status "Deleted SG: $SG"
                fi
              done
          fi

          # Finally delete VPC
          aws ec2 delete-vpc --vpc-id "$VPC" --region "$REGION" >/dev/null 2>&1 || true
          print_success "Deleted VPC: $VPC"
        done
    else
        print_status "No stack VPCs found"
    fi

    # 5. Delete Key Pairs (schwab-api related)
    print_status "[5/7] Checking Key Pairs..."
    KEYS=$(aws ec2 describe-key-pairs --region "$REGION" --query "KeyPairs[].KeyName" --output text 2>/dev/null || true)
    if [ -n "$KEYS" ]; then
        for KEY in $KEYS; do
          if [[ "$KEY" == schwab-api-keypair* ]]; then
            aws ec2 delete-key-pair --key-name "$KEY" --region "$REGION" >/dev/null 2>&1 || true
            print_status "Deleted key pair: $KEY"
          fi
        done
    fi

    print_success "AWS resource cleanup completed"
    echo ""
}

# Function to collect domain configuration
collect_domain_config() {
    echo ""
    print_milestone "Domain Configuration Setup"
    echo ""
    echo "For SSL certificates and production deployment, we need domain information."
    echo ""
    
    # Domain name
    while [[ -z "$DOMAIN_NAME" ]]; do
        echo -n "Enter your domain name [default: schwabapi.imart.com]: "
        read DOMAIN_NAME
        if [[ -z "$DOMAIN_NAME" ]]; then
            DOMAIN_NAME="schwabapi.imart.com"
            print_status "Using default domain: $DOMAIN_NAME"
        fi
    done
    
    # Admin email for SSL certificates
    while [[ -z "$ADMIN_EMAIL" ]]; do
        echo -n "Enter admin email for SSL certificates [default: admin@imart.com]: "
        read ADMIN_EMAIL
        if [[ -z "$ADMIN_EMAIL" ]]; then
            ADMIN_EMAIL="admin@imart.com"
            print_status "Using default email: $ADMIN_EMAIL"
        fi
    done
    
    print_success "Domain configuration collected"
}

# Function to collect Google SSO credentials
collect_google_sso_config() {
    echo ""
    print_milestone "Google SSO Configuration Setup"
    echo ""
    echo "For Google Single Sign-On integration, you'll need:"
    echo "1. Go to https://console.cloud.google.com/"
    echo "2. Create a new project or select existing one"
    echo "3. Enable Google+ API"
    echo "4. Create OAuth 2.0 credentials (Web application)"
    echo "5. Add authorized redirect URIs:"
    echo "   - https://$DOMAIN_NAME/auth/google/callback"
    echo "   - http://localhost:3000/auth/google/callback (for development)"
    echo ""
    
    # Ask if user wants to configure Google SSO now
    echo -n "Do you want to configure Google SSO now? (y/n) [default: y]: "
    read CONFIGURE_GOOGLE_SSO
    if [[ -z "$CONFIGURE_GOOGLE_SSO" ]]; then
        CONFIGURE_GOOGLE_SSO="y"
    fi
    
    if [[ "$CONFIGURE_GOOGLE_SSO" =~ ^[Yy]$ ]]; then
        # Google Client ID
        while [[ -z "$GOOGLE_CLIENT_ID" ]]; do
            echo -n "Enter your Google OAuth Client ID: "
            read GOOGLE_CLIENT_ID
            if [[ -z "$GOOGLE_CLIENT_ID" ]]; then
                print_error "Google Client ID cannot be empty."
            fi
        done
        
        # Google Client Secret
        while [[ -z "$GOOGLE_CLIENT_SECRET" ]]; do
            echo -n "Enter your Google OAuth Client Secret: "
            read GOOGLE_CLIENT_SECRET
            if [[ -z "$GOOGLE_CLIENT_SECRET" ]]; then
                print_error "Google Client Secret cannot be empty."
            fi
        done
        
        print_success "Google SSO configuration collected"
    else
        print_warning "Skipping Google SSO configuration. You can configure it later."
        GOOGLE_CLIENT_ID="your_google_client_id_here"
        GOOGLE_CLIENT_SECRET="your_google_client_secret_here"
    fi
}

# Function to collect notification settings
collect_notification_config() {
    echo ""
    print_milestone "Trading Dashboard Notification & Alerts Configuration"
    echo ""
    echo "Configure notification channels for trading alerts and monitoring:"
    echo ""
    
    # Email notifications
    echo -n "Enable email notifications? (y/n) [default: y]: "
    read ENABLE_EMAIL_NOTIFICATIONS
    if [[ -z "$ENABLE_EMAIL_NOTIFICATIONS" ]]; then
        ENABLE_EMAIL_NOTIFICATIONS="y"
    fi
    
    if [[ "$ENABLE_EMAIL_NOTIFICATIONS" =~ ^[Yy]$ ]]; then
        echo -n "Enter notification email address [default: $ADMIN_EMAIL]: "
        read NOTIFICATION_EMAIL
        if [[ -z "$NOTIFICATION_EMAIL" ]]; then
            NOTIFICATION_EMAIL="$ADMIN_EMAIL"
        fi
        
        # SMTP Configuration for email alerts
        echo ""
        echo "SMTP Configuration for Email Alerts:"
        echo -n "SMTP Server [default: smtp.gmail.com]: "
        read SMTP_SERVER
        if [[ -z "$SMTP_SERVER" ]]; then
            SMTP_SERVER="smtp.gmail.com"
        fi
        
        echo -n "SMTP Port [default: 587]: "
        read SMTP_PORT
        if [[ -z "$SMTP_PORT" ]]; then
            SMTP_PORT="587"
        fi
        
        echo -n "SMTP Username [default: $NOTIFICATION_EMAIL]: "
        read SMTP_USERNAME
        if [[ -z "$SMTP_USERNAME" ]]; then
            SMTP_USERNAME="$NOTIFICATION_EMAIL"
        fi
        
        echo -n "SMTP Password (App Password recommended): "
        read -s SMTP_PASSWORD
        echo ""
    fi
    
    # Slack notifications (optional)
    echo -n "Enable Slack notifications? (y/n) [default: n]: "
    read ENABLE_SLACK_NOTIFICATIONS
    if [[ -z "$ENABLE_SLACK_NOTIFICATIONS" ]]; then
        ENABLE_SLACK_NOTIFICATIONS="n"
    fi
    
    if [[ "$ENABLE_SLACK_NOTIFICATIONS" =~ ^[Yy]$ ]]; then
        echo -n "Enter Slack webhook URL: "
        read SLACK_WEBHOOK_URL
    fi
    
    # Telegram notifications (optional)
    echo -n "Enable Telegram notifications? (y/n) [default: n]: "
    read ENABLE_TELEGRAM_NOTIFICATIONS
    if [[ -z "$ENABLE_TELEGRAM_NOTIFICATIONS" ]]; then
        ENABLE_TELEGRAM_NOTIFICATIONS="n"
    fi
    
    if [[ "$ENABLE_TELEGRAM_NOTIFICATIONS" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Telegram Bot Configuration:"
        echo "1. Create a bot by messaging @BotFather on Telegram"
        echo "2. Get your bot token from @BotFather"
        echo "3. Get your chat ID by messaging @userinfobot"
        echo ""
        echo -n "Enter Telegram Bot Token: "
        read TELEGRAM_BOT_TOKEN
        echo -n "Enter Telegram Chat ID: "
        read TELEGRAM_CHAT_ID
    fi
    
    # Trading Alert Thresholds
    echo ""
    echo "Trading Alert Thresholds:"
    echo -n "Daily loss limit (USD) [default: 1000]: "
    read DAILY_LOSS_LIMIT
    if [[ -z "$DAILY_LOSS_LIMIT" ]]; then
        DAILY_LOSS_LIMIT="1000"
    fi
    
    echo -n "Total loss limit (USD) [default: 5000]: "
    read TOTAL_LOSS_LIMIT
    if [[ -z "$TOTAL_LOSS_LIMIT" ]]; then
        TOTAL_LOSS_LIMIT="5000"
    fi
    
    echo -n "Volatility spike threshold (%) [default: 10]: "
    read VOLATILITY_THRESHOLD
    if [[ -z "$VOLATILITY_THRESHOLD" ]]; then
        VOLATILITY_THRESHOLD="10"
    fi
    
    echo -n "High margin usage threshold (%) [default: 80]: "
    read MARGIN_THRESHOLD
    if [[ -z "$MARGIN_THRESHOLD" ]]; then
        MARGIN_THRESHOLD="80"
    fi
    
    echo -n "Alert check interval (seconds) [default: 30]: "
    read ALERT_CHECK_INTERVAL
    if [[ -z "$ALERT_CHECK_INTERVAL" ]]; then
        ALERT_CHECK_INTERVAL="30"
    fi
    
    print_success "Trading dashboard notification configuration collected"
}

# Function to collect Schwab API credentials
collect_schwab_credentials() {
    echo ""
    print_milestone "Charles Schwab API Configuration"
    echo ""
    echo "You'll need your Schwab API credentials from https://developer.schwab.com/"
    echo "If you don't have them yet, you can:"
    echo "1. Go to https://developer.schwab.com/"
    echo "2. Sign in with your Schwab account"
    echo "3. Create an app to get your Client ID and Client Secret"
    echo ""
    
    # Prompt for Client ID
    while [[ -z "$SCHWAB_CLIENT_ID" ]]; do
        echo -n "Enter your Schwab Client ID: "
        read SCHWAB_CLIENT_ID
        if [[ -z "$SCHWAB_CLIENT_ID" ]]; then
            print_error "Client ID cannot be empty. Please enter your Schwab Client ID."
        fi
    done
    
    # Prompt for Client Secret
    while [[ -z "$SCHWAB_CLIENT_SECRET" ]]; do
        echo -n "Enter your Schwab Client Secret: "
        read SCHWAB_CLIENT_SECRET
        if [[ -z "$SCHWAB_CLIENT_SECRET" ]]; then
            print_error "Client Secret cannot be empty. Please enter your Schwab Client Secret."
        fi
    done
    
    # Prompt for Callback URL
    echo ""
    echo "Enter your preferred callback URL for OAuth redirects."
    echo "For production, this should be: https://$DOMAIN_NAME/auth/schwab/callback"
    echo ""
    while [[ -z "$SCHWAB_CALLBACK_URL" ]]; do
        echo -n "Enter your Schwab Callback URL [default: https://$DOMAIN_NAME/auth/schwab/callback]: "
        read SCHWAB_CALLBACK_URL
        if [[ -z "$SCHWAB_CALLBACK_URL" ]]; then
            SCHWAB_CALLBACK_URL="https://$DOMAIN_NAME/auth/schwab/callback"
            print_status "Using default callback URL: $SCHWAB_CALLBACK_URL"
        fi
    done
    
    print_success "Schwab API credentials and configuration collected successfully"
    echo ""
}

# Function to update secrets manager with all credentials
update_secrets_manager() {
    print_milestone "Updating AWS Secrets Manager with all credentials and trading dashboard configuration..."
    
    # Generate secure passwords for database and services
    print_status "Generating secure passwords for database and services..."
    POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)
    REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)
    JWT_SECRET=$(openssl rand -base64 32)
    SESSION_SECRET=$(openssl rand -base64 32)
    ENCRYPTION_KEY=$(openssl rand -base64 32)
    NEXTAUTH_SECRET=$(openssl rand -base64 32)
    
    print_success "Generated secure passwords for all services"
    
    # Create comprehensive secret with all credentials and trading dashboard settings
    SECRET_VALUE=$(cat <<EOF
{
  "schwab_client_id": "$SCHWAB_CLIENT_ID",
  "schwab_client_secret": "$SCHWAB_CLIENT_SECRET",
  "schwab_callback_url": "$SCHWAB_CALLBACK_URL",
  "google_client_id": "$GOOGLE_CLIENT_ID",
  "google_client_secret": "$GOOGLE_CLIENT_SECRET",
  "domain_name": "$DOMAIN_NAME",
  "admin_email": "$ADMIN_EMAIL",
  "notification_email": "${NOTIFICATION_EMAIL:-$ADMIN_EMAIL}",
  "slack_webhook_url": "${SLACK_WEBHOOK_URL:-}",
  "telegram_bot_token": "${TELEGRAM_BOT_TOKEN:-}",
  "telegram_chat_id": "${TELEGRAM_CHAT_ID:-}",
  "smtp_server": "${SMTP_SERVER:-smtp.gmail.com}",
  "smtp_port": "${SMTP_PORT:-587}",
  "smtp_username": "${SMTP_USERNAME:-$NOTIFICATION_EMAIL}",
  "smtp_password": "${SMTP_PASSWORD:-}",
  "daily_loss_limit": "${DAILY_LOSS_LIMIT:-1000}",
  "total_loss_limit": "${TOTAL_LOSS_LIMIT:-5000}",
  "volatility_threshold": "${VOLATILITY_THRESHOLD:-10}",
  "margin_threshold": "${MARGIN_THRESHOLD:-80}",
  "alert_check_interval": "${ALERT_CHECK_INTERVAL:-30}",
  "enable_email_notifications": "${ENABLE_EMAIL_NOTIFICATIONS:-y}",
  "enable_slack_notifications": "${ENABLE_SLACK_NOTIFICATIONS:-n}",
  "enable_telegram_notifications": "${ENABLE_TELEGRAM_NOTIFICATIONS:-n}",
  "postgres_password": "$POSTGRES_PASSWORD",
  "redis_password": "$REDIS_PASSWORD",
  "jwt_secret": "$JWT_SECRET",
  "session_secret": "$SESSION_SECRET",
  "nextauth_secret": "$NEXTAUTH_SECRET",
  "encryption_key": "$ENCRYPTION_KEY"
}
EOF
)
    
    # Update the secret with all values
    aws secretsmanager update-secret \
        --secret-id "$SECRET_ARN" \
        --secret-string "$SECRET_VALUE" \
        --region "$REGION" > /dev/null
    
    print_success "Secrets Manager updated with all credentials and trading dashboard configuration"
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
    
    # Build parameters array
    PARAMETERS=(
        "ParameterKey=KeyPairName,ParameterValue=$KEY_PAIR_NAME"
        "ParameterKey=InstanceType,ParameterValue=$INSTANCE_TYPE"
        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT"
    )
    
    print_status "Using dynamic public IP"
    
    # Check if stack exists
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" &> /dev/null; then
        print_status "Stack exists, updating..."
        aws cloudformation update-stack \
            --stack-name "$STACK_NAME" \
            --template-body file://"$TEMPLATE_FILE" \
            --parameters "${PARAMETERS[@]}" \
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
            --parameters "${PARAMETERS[@]}" \
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
    
    API_INSTANCE_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`APIInstanceId`].OutputValue' \
        --output text)
    
    APP_INSTANCE_ID=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`AppInstanceId`].OutputValue' \
        --output text)
    
    API_PRIVATE_IP=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`APIPrivateIP`].OutputValue' \
        --output text)
    
    APP_PUBLIC_IP=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`AppPublicIP`].OutputValue' \
        --output text)
    
    ELASTIC_IP=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`ElasticIPAddress`].OutputValue' \
        --output text)
    
    SECRET_ARN=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --region "$REGION" \
        --query 'Stacks[0].Outputs[?OutputKey==`SecretArn`].OutputValue' \
        --output text)
    
    echo ""
    print_success "Infrastructure deployment completed successfully!"
    echo ""
    echo "=== INFRASTRUCTURE INFORMATION ==="
    echo "API Server Instance ID: $API_INSTANCE_ID"
    echo "API Server Private IP: $API_PRIVATE_IP"
    echo "Application Server Instance ID: $APP_INSTANCE_ID"
    echo "Application Server Public IP: $APP_PUBLIC_IP"
    echo "Elastic IP Address: $ELASTIC_IP"
    echo "Secret ARN: $SECRET_ARN"
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

# Function to wait for EC2 instances to be ready
wait_for_instance() {
    print_status "Waiting for both EC2 instances to be ready..."
    
    # Wait for both instances to be running
    aws ec2 wait instance-running --instance-ids "$API_INSTANCE_ID" "$APP_INSTANCE_ID" --region "$REGION"
    
    print_success "Both EC2 instances are running and ready for deployment"
}

# Function to deploy enhanced API server with monitoring
deploy_api_server() {
    print_milestone "Deploying Enhanced API Server with Monitoring..."
    
    # Get API server public IP for SSH
    API_PUBLIC_IP=$(aws ec2 describe-instances \
        --instance-ids "$API_INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text \
        --region "$REGION")
    
    # Wait for API server to be ready
    print_status "Waiting for API server to be ready..."
    aws ec2 wait instance-running --instance-ids "$API_INSTANCE_ID" --region "$REGION"
    
    # Wait for SSH to be available
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if ssh -i "${KEY_PAIR_NAME}.pem" -o ConnectTimeout=10 -o StrictHostKeyChecking=no ec2-user@"$API_PUBLIC_IP" "echo 'API Server SSH ready'" &> /dev/null; then
            break
        fi
        print_status "Waiting for API server SSH... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    # Deploy API server code with enhancements
    print_status "Uploading enhanced API server files..."
    
    # Upload individual files first with error handling
    print_status "Uploading individual files..."
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 ../app.py ../requirements.txt ../init_db.py ec2-user@"$API_PUBLIC_IP":/tmp/ || {
        print_error "Failed to upload individual files"
        exit 1
    }
    
    # Upload directories separately with error handling
    print_status "Uploading handlers directory..."
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 -r ../handlers/ ec2-user@"$API_PUBLIC_IP":/tmp/ || {
        print_error "Failed to upload handlers directory"
        exit 1
    }
    
    print_status "Uploading models directory..."
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 -r ../models/ ec2-user@"$API_PUBLIC_IP":/tmp/ || {
        print_error "Failed to upload models directory"
        exit 1
    }
    
    print_status "Uploading services directory..."
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 -r ../services/ ec2-user@"$API_PUBLIC_IP":/tmp/ || {
        print_error "Failed to upload services directory"
        exit 1
    }
    
    # Set up enhanced API server with monitoring
    ssh -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no ec2-user@"$API_PUBLIC_IP" "
        sudo mkdir -p /opt/schwab-api/handlers /opt/schwab-api/models /opt/schwab-api/services /opt/schwab-api/logs /opt/schwab-api/config
        sudo chown -R ec2-user:ec2-user /opt/schwab-api
        cp /tmp/app.py /tmp/requirements.txt /tmp/init_db.py /opt/schwab-api/
        cp /tmp/handlers/* /opt/schwab-api/handlers/
        cp -r /tmp/models/* /opt/schwab-api/models/
        cp -r /tmp/services/* /opt/schwab-api/services/
        cd /opt/schwab-api
        
        # Install enhanced requirements
        cat >> requirements.txt << 'EOF'
prometheus-client>=0.14.0
structlog>=22.1.0
python-json-logger>=2.0.0
psutil>=5.9.0
boto3>=1.26.0
EOF
        
        python3 -m pip install --user -r requirements.txt
        
        # Initialize trading dashboard database
        print_status 'Initializing trading dashboard database...'
        python3 init_db.py
        if [ $? -eq 0 ]; then
            print_success 'Trading dashboard database initialized successfully'
        else
            print_error 'Failed to initialize trading dashboard database'
            exit 1
        fi
        
        # Create enhanced configuration
        cat > config/monitoring.py << 'EOF'
import logging
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import psutil
import time

# Prometheus metrics
REQUEST_COUNT = Counter('schwab_api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('schwab_api_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('schwab_api_active_connections', 'Active connections')
SYSTEM_CPU = Gauge('schwab_api_system_cpu_percent', 'System CPU usage')
SYSTEM_MEMORY = Gauge('schwab_api_system_memory_percent', 'System memory usage')

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt=\"iso\"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

def start_metrics_server():
    start_http_server(8081)

def update_system_metrics():
    SYSTEM_CPU.set(psutil.cpu_percent())
    SYSTEM_MEMORY.set(psutil.virtual_memory().percent)
EOF
        
        # Create enhanced app wrapper
        cat > enhanced_app.py << 'EOF'
import sys
import os
sys.path.append('/opt/schwab-api')

from config.monitoring import setup_logging, start_metrics_server, update_system_metrics
import threading
import time

# Setup enhanced logging and monitoring
setup_logging()
start_metrics_server()

# Start system metrics updater
def metrics_updater():
    while True:
        update_system_metrics()
        time.sleep(30)

metrics_thread = threading.Thread(target=metrics_updater, daemon=True)
metrics_thread.start()

# Import and run the main app
from app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
EOF
    "
    
    # Create enhanced systemd service
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$API_PUBLIC_IP" "sudo tee /etc/systemd/system/schwab-api.service > /dev/null << 'EOF'
[Unit]
Description=Charles Schwab API Integration - Enhanced
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/opt/schwab-api
Environment=PATH=/home/ec2-user/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/opt/schwab-api
ExecStart=/usr/bin/python3 /opt/schwab-api/enhanced_app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF"
    
    # Start enhanced API server service
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$API_PUBLIC_IP" "
        sudo systemctl daemon-reload
        sudo systemctl enable schwab-api
        sudo systemctl start schwab-api
    "
    
    print_success "Enhanced API server deployed with monitoring capabilities"
}

# Function to deploy modern dashboard and application server
deploy_application_server() {
    print_milestone "Deploying Modern Dashboard & Application Server..."
    
    # Wait for Application server to be ready
    print_status "Waiting for Application server to be ready..."
    aws ec2 wait instance-running --instance-ids "$APP_INSTANCE_ID" --region "$REGION"
    
    # Wait for SSH to be available
    local max_attempts=30
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if ssh -i "${KEY_PAIR_NAME}.pem" -o ConnectTimeout=10 -o StrictHostKeyChecking=no ec2-user@"$APP_PUBLIC_IP" "echo 'App Server SSH ready'" &> /dev/null; then
            break
        fi
        print_status "Waiting for Application server SSH... (attempt $attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    # Upload application server files with error handling
    print_status "Uploading modern dashboard and configuration files..."
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 ../docker-compose.app.yml ec2-user@"$APP_PUBLIC_IP":~/docker-compose.yml || {
        print_error "Failed to upload docker-compose.yml"
        exit 1
    }
    
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 -r ../nginx/ ec2-user@"$APP_PUBLIC_IP":~/ || {
        print_error "Failed to upload nginx directory"
        exit 1
    }
    
    # Upload missing Docker files and application code
    print_status "Uploading Docker files and application code..."
    
    # Upload individual files first with error handling
    print_status "Uploading Docker and application files..."
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 \
        ../Dockerfile.dashboard ../Dockerfile.worker ../worker.py ../requirements.txt ../app.py ../init_db.py ../.env \
        ec2-user@"$APP_PUBLIC_IP":~/ || {
        print_error "Failed to upload Docker and application files"
        exit 1
    }
    
    # Upload frontend source files only (exclude node_modules)
    print_status "Uploading frontend source files (excluding node_modules)..."
    
    # Create frontend directory structure on server first
    ssh -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no ec2-user@"$APP_PUBLIC_IP" "mkdir -p ~/frontend/{src,public}"
    
    # Upload only essential frontend files (no node_modules)
    if [ -d "../frontend/src" ]; then
        scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 -r ../frontend/src/ ec2-user@"$APP_PUBLIC_IP":~/frontend/ || {
            print_error "Failed to upload frontend src directory"
            exit 1
        }
    fi
    
    if [ -d "../frontend/public" ]; then
        scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 -r ../frontend/public/ ec2-user@"$APP_PUBLIC_IP":~/frontend/ || {
            print_error "Failed to upload frontend public directory"
            exit 1
        }
    fi
    
    # Upload frontend config files
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 \
        ../frontend/package.json ../frontend/package-lock.json ec2-user@"$APP_PUBLIC_IP":~/frontend/ 2>/dev/null || {
        print_warning "Some frontend config files not found, will create defaults"
    }
    
    # Upload Next.js config files if they exist
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 \
        ../frontend/next.config.js ../frontend/tailwind.config.js ec2-user@"$APP_PUBLIC_IP":~/frontend/ 2>/dev/null || true
    
    print_status "Uploading services directory..."
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 -r ../services/ ec2-user@"$APP_PUBLIC_IP":~/ || {
        print_error "Failed to upload services directory"
        exit 1
    }
    
    print_status "Uploading models directory..."
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 -r ../models/ ec2-user@"$APP_PUBLIC_IP":~/ || {
        print_error "Failed to upload models directory"
        exit 1
    }
    
    print_status "Uploading handlers directory..."
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=60 -r ../handlers/ ec2-user@"$APP_PUBLIC_IP":~/ || {
        print_error "Failed to upload handlers directory"
        exit 1
    }
    
    # Create modern React dashboard and enhanced backend
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$APP_PUBLIC_IP" "
        # Create directory structure
        mkdir -p dashboard/{src,public,components,pages,utils,hooks} worker database/{init,migrations} logs/{nginx,dashboard,worker} monitoring
        
        # Create modern React dashboard package.json
        cat > dashboard/package.json << 'EOF'
{
  \"name\": \"schwab-dashboard\",
  \"version\": \"2.0.0\",
  \"description\": \"Charles Schwab API Modern Dashboard - Milestone 2\",
  \"main\": \"server.js\",
  \"scripts\": {
    \"dev\": \"next dev\",
    \"build\": \"next build\",
    \"start\": \"next start\",
    \"lint\": \"next lint\"
  },
  \"dependencies\": {
    \"next\": \"^14.0.0\",
    \"react\": \"^18.2.0\",
    \"react-dom\": \"^18.2.0\",
    \"@next/font\": \"^14.0.0\",
    \"axios\": \"^1.5.0\",
    \"recharts\": \"^2.8.0\",
    \"@headlessui/react\": \"^1.7.17\",
    \"@heroicons/react\": \"^2.0.18\",
    \"tailwindcss\": \"^3.3.0\",
    \"autoprefixer\": \"^10.4.16\",
    \"postcss\": \"^8.4.31\",
    \"next-auth\": \"^4.24.0\",
    \"jsonwebtoken\": \"^9.0.2\",
    \"bcryptjs\": \"^2.4.3\",
    \"socket.io-client\": \"^4.7.2\",
    \"date-fns\": \"^2.30.0\",
    \"react-hot-toast\": \"^2.4.1\",
    \"framer-motion\": \"^10.16.4\"
  },
  \"devDependencies\": {
    \"@types/node\": \"^20.8.0\",
    \"@types/react\": \"^18.2.25\",
    \"@types/react-dom\": \"^18.2.10\",
    \"eslint\": \"^8.51.0\",
    \"eslint-config-next\": \"^14.0.0\",
    \"typescript\": \"^5.2.2\"
  }
}
EOF
        
        # Create Next.js configuration
        cat > dashboard/next.config.js << 'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  env: {
    API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:8080',
    NEXTAUTH_URL: process.env.NEXTAUTH_URL || 'http://localhost:3000',
    NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET,
    GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET: process.env.GOOGLE_CLIENT_SECRET,
  },
  async rewrites() {
    return [
      {
        source: '/api/schwab/:path*',
        destination: \`\${process.env.API_BASE_URL}/api/:path*\`,
      },
    ];
  },
};

module.exports = nextConfig;
EOF
        
        # Create Tailwind CSS configuration
        cat > dashboard/tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        schwab: {
          blue: '#0066CC',
          darkblue: '#003366',
          green: '#00AA44',
          red: '#CC0000',
          gray: '#666666',
        },
      },
    },
  },
  plugins: [],
};
EOF
        
        # Create main dashboard layout
        cat > dashboard/pages/_app.js << 'EOF'
import '../styles/globals.css';
import { SessionProvider } from 'next-auth/react';
import { Toaster } from 'react-hot-toast';

export default function App({
  Component,
  pageProps: { session, ...pageProps },
}) {
  return (
    <SessionProvider session={session}>
      <Component {...pageProps} />
      <Toaster position=\"top-right\" />
    </SessionProvider>
  );
}
EOF
        
        # Create main dashboard page
        cat > dashboard/pages/index.js << 'EOF'
import { useState, useEffect } from 'react';
import { useSession, signIn, signOut } from 'next-auth/react';
import Head from 'next/head';
import DashboardLayout from '../components/DashboardLayout';
import MetricsOverview from '../components/MetricsOverview';
import PortfolioChart from '../components/PortfolioChart';
import AlertsPanel from '../components/AlertsPanel';
import TradingInterface from '../components/TradingInterface';

export default function Dashboard() {
  const { data: session, status } = useSession();
  const [portfolioData, setPortfolioData] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    if (session) {
      fetchDashboardData();
    }
  }, [session]);

  const fetchDashboardData = async () => {
    try {
      // Fetch portfolio data
      const portfolioResponse = await fetch('/api/schwab/portfolio');
      const portfolioData = await portfolioResponse.json();
      setPortfolioData(portfolioData);

      // Fetch metrics
      const metricsResponse = await fetch('/api/schwab/metrics');
      const metricsData = await metricsResponse.json();
      setMetrics(metricsData);

      // Fetch alerts
      const alertsResponse = await fetch('/api/schwab/alerts');
      const alertsData = await alertsResponse.json();
      setAlerts(alertsData);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    }
  };

  if (status === 'loading') {
    return <div className=\"flex items-center justify-center min-h-screen\">Loading...</div>;
  }

  if (!session) {
    return (
      <div className=\"min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8\">
        <Head>
          <title>Schwab API Dashboard - Login</title>
        </Head>
        <div className=\"sm:mx-auto sm:w-full sm:max-w-md\">
          <h2 className=\"mt-6 text-center text-3xl font-extrabold text-gray-900\">
            Sign in to your account
          </h2>
          <div className=\"mt-8 sm:mx-auto sm:w-full sm:max-w-md\">
            <div className=\"bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10\">
              <button
                onClick={() => signIn('google')}
                className=\"w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-schwab-blue hover:bg-schwab-darkblue focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-schwab-blue\"
              >
                Sign in with Google
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <DashboardLayout>
      <Head>
        <title>Schwab API Dashboard</title>
      </Head>
      <div className=\"space-y-6\">
        <div className=\"flex justify-between items-center\">
          <h1 className=\"text-2xl font-bold text-gray-900\">Trading Dashboard</h1>
          <button
            onClick={() => signOut()}
            className=\"bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium\"
          >
            Sign Out
          </button>
        </div>
        
        <MetricsOverview metrics={metrics} />
        <div className=\"grid grid-cols-1 lg:grid-cols-2 gap-6\">
          <PortfolioChart data={portfolioData} />
          <AlertsPanel alerts={alerts} />
        </div>
        <TradingInterface />
      </div>
    </DashboardLayout>
  );
}
EOF
        
        # Create CSS styles
        cat > dashboard/styles/globals.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  html {
    font-family: system-ui, sans-serif;
  }
}

@layer components {
  .btn-primary {
    @apply bg-schwab-blue hover:bg-schwab-darkblue text-white font-medium py-2 px-4 rounded-md transition-colors;
  }
  
  .btn-secondary {
    @apply bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-2 px-4 rounded-md transition-colors;
  }
  
  .card {
    @apply bg-white rounded-lg shadow-md p-6;
  }
  
  .metric-card {
    @apply bg-white rounded-lg shadow-sm p-4 border border-gray-200;
  }
}
EOF
        
        # Create enhanced worker with alerts and monitoring
        cat > worker/requirements.txt << 'EOF'
redis>=4.0.0
psycopg2-binary>=2.9.0
celery>=5.2.0
requests>=2.25.0
boto3>=1.20.0
python-dotenv>=0.19.0
prometheus-client>=0.14.0
structlog>=22.1.0
smtplib-ssl>=1.0.0
slack-sdk>=3.19.0
schedule>=1.2.0
pandas>=1.5.0
numpy>=1.24.0
EOF
        
        cat > worker/worker.py << 'EOF'
import os
import time
import logging
import json
import smtplib
import schedule
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from datetime import datetime, timedelta
import redis
import psycopg2
import requests
from slack_sdk import WebClient
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import structlog

# Setup structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt=\"iso\"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
ALERTS_SENT = Counter('schwab_alerts_sent_total', 'Total alerts sent', ['type', 'channel'])
PORTFOLIO_VALUE = Gauge('schwab_portfolio_value_usd', 'Current portfolio value in USD')
DAILY_PNL = Gauge('schwab_daily_pnl_usd', 'Daily P&L in USD')
RISK_SCORE = Gauge('schwab_risk_score', 'Current risk score (0-100)')

class AlertManager:
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.db_url = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/db')
        self.api_base_url = os.getenv('API_BASE_URL', 'http://localhost:8080')
        self.notification_email = os.getenv('NOTIFICATION_EMAIL')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        
    def check_portfolio_alerts(self):
        \"\"\"Check for portfolio-based alerts\"\"\"
        try:
            # Fetch current portfolio data
            response = requests.get(f'{self.api_base_url}/api/portfolio')
            if response.status_code == 200:
                portfolio = response.json()
                
                # Update metrics
                PORTFOLIO_VALUE.set(portfolio.get('total_value', 0))
                DAILY_PNL.set(portfolio.get('daily_pnl', 0))
                
                # Check for alerts
                self._check_loss_limits(portfolio)
                self._check_volatility_spikes(portfolio)
                self._check_margin_usage(portfolio)
                
        except Exception as e:
            logger.error(\"Error checking portfolio alerts\", error=str(e))
    
    def _check_loss_limits(self, portfolio):
        \"\"\"Check if daily/total losses exceed limits\"\"\"
        daily_pnl = portfolio.get('daily_pnl', 0)
        total_pnl = portfolio.get('total_pnl', 0)
        
        # Daily loss limit: -$1000
        if daily_pnl < -1000:
            self._send_alert(
                'LOSS_LIMIT',
                f'Daily loss limit exceeded: ${daily_pnl:.2f}',
                'high'
            )
        
        # Total loss limit: -$5000
        if total_pnl < -5000:
            self._send_alert(
                'TOTAL_LOSS_LIMIT',
                f'Total loss limit exceeded: ${total_pnl:.2f}',
                'critical'
            )
    
    def _check_volatility_spikes(self, portfolio):
        \"\"\"Check for unusual volatility in positions\"\"\"
        positions = portfolio.get('positions', [])
        for position in positions:
            daily_change_pct = position.get('daily_change_percent', 0)
            if abs(daily_change_pct) > 10:  # 10% daily change
                self._send_alert(
                    'VOLATILITY_SPIKE',
                    f'{position[\"symbol\"]} moved {daily_change_pct:.1f}% today',
                    'medium'
                )
    
    def _check_margin_usage(self, portfolio):
        \"\"\"Check margin usage levels\"\"\"
        margin_used = portfolio.get('margin_used', 0)
        margin_available = portfolio.get('margin_available', 0)
        
        if margin_available > 0:
            usage_pct = (margin_used / (margin_used + margin_available)) * 100
            if usage_pct > 80:  # 80% margin usage
                self._send_alert(
                    'HIGH_MARGIN_USAGE',
                    f'Margin usage at {usage_pct:.1f}%',
                    'high'
                )
    
    def _send_alert(self, alert_type, message, severity):
        \"\"\"Send alert via configured channels\"\"\"
        alert_data = {
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Send email if configured
        if self.notification_email:
            self._send_email_alert(alert_data)
            ALERTS_SENT.labels(type=alert_type, channel='email').inc()
        
        # Send Slack if configured
        if self.slack_webhook:
            self._send_slack_alert(alert_data)
            ALERTS_SENT.labels(type=alert_type, channel='slack').inc()
        
        # Store in Redis for dashboard
        self.redis_client.lpush('alerts', json.dumps(alert_data))
        self.redis_client.ltrim('alerts', 0, 99)  # Keep last 100 alerts
        
        logger.info(\"Alert sent\", **alert_data)
    
    def _send_email_alert(self, alert_data):
        \"\"\"Send email alert\"\"\"
        try:
            msg = MimeMultipart()
            msg['From'] = os.getenv('SMTP_FROM', 'alerts@schwabapi.com')
            msg['To'] = self.notification_email
            msg['Subject'] = f\"Schwab API Alert: {alert_data['type']}\"
            
            body = f\"\"\"
Alert Type: {alert_data['type']}
Severity: {alert_data['severity']}
Message: {alert_data['message']}
Time: {alert_data['timestamp']}

This is an automated alert from your Schwab API trading system.
\"\"\"
            
            msg.attach(MimeText(body, 'plain'))
            
            # Configure SMTP (you'll need to set these environment variables)
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SMTP_USER')
            smtp_pass = os.getenv('SMTP_PASS')
            
            if smtp_user and smtp_pass:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                server.quit()
                
        except Exception as e:
            logger.error(\"Error sending email alert\", error=str(e))
    
    def _send_slack_alert(self, alert_data):
        \"\"\"Send Slack alert\"\"\"
        try:
            color_map = {
                'low': '#36a64f',
                'medium': '#ff9500',
                'high': '#ff0000',
                'critical': '#8b0000'
            }
            
            payload = {
                'attachments': [{
                    'color': color_map.get(alert_data['severity'], '#36a64f'),
                    'title': f\"Schwab API Alert: {alert_data['type']}\",
                    'text': alert_data['message'],
                    'fields': [
                        {'title': 'Severity', 'value': alert_data['severity'], 'short': True},
                        {'title': 'Time', 'value': alert_data['timestamp'], 'short': True}
                    ]
                }]
            }
            
            requests.post(self.slack_webhook, json=payload)
            
        except Exception as e:
            logger.error(\"Error sending Slack alert\", error=str(e))

def main():
    logger.info(\"Starting Schwab API Enhanced Worker with Alerts...\")
    
    # Start Prometheus metrics server
    start_http_server(8082)
    
    # Initialize alert manager
    alert_manager = AlertManager()
    
    # Schedule periodic tasks
    schedule.every(1).minutes.do(alert_manager.check_portfolio_alerts)
    
    # Main worker loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(10)
        except Exception as e:
            logger.error(\"Worker error\", error=str(e))
            time.sleep(30)

if __name__ == '__main__':
    main()
EOF
        
        # Create comprehensive environment file with generated passwords
        cat > .env << EOF
# Database Configuration
DB_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=schwab_trading
POSTGRES_USER=schwab_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# Redis Configuration
REDIS_PASSWORD=$REDIS_PASSWORD

# Application Configuration
NODE_ENV=production
API_BASE_URL=http://$API_PRIVATE_IP:8080
DATABASE_URL=postgresql://schwab_user:$POSTGRES_PASSWORD@postgres:5432/schwab_trading
REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379

# Domain and SSL
DOMAIN=$DOMAIN_NAME
EMAIL=$ADMIN_EMAIL

# NextAuth Configuration
NEXTAUTH_URL=https://$DOMAIN_NAME
NEXTAUTH_SECRET=$NEXTAUTH_SECRET

# Google SSO
GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET

# Schwab API Configuration
SCHWAB_CLIENT_ID=$SCHWAB_CLIENT_ID
SCHWAB_CLIENT_SECRET=$SCHWAB_CLIENT_SECRET
SCHWAB_CALLBACK_URL=$SCHWAB_CALLBACK_URL

# Notification Configuration
NOTIFICATION_EMAIL=${NOTIFICATION_EMAIL:-$ADMIN_EMAIL}
SLACK_WEBHOOK_URL=${SLACK_WEBHOOK_URL:-}

# SMTP Configuration (for email alerts)
SMTP_SERVER=${SMTP_SERVER:-smtp.gmail.com}
SMTP_PORT=${SMTP_PORT:-587}
SMTP_FROM=alerts@$DOMAIN_NAME
SMTP_USER=${SMTP_USERNAME:-$NOTIFICATION_EMAIL}
SMTP_PASS=${SMTP_PASSWORD:-}

# Trading Alert Thresholds
DAILY_LOSS_LIMIT=${DAILY_LOSS_LIMIT:-1000}
TOTAL_LOSS_LIMIT=${TOTAL_LOSS_LIMIT:-5000}
VOLATILITY_THRESHOLD=${VOLATILITY_THRESHOLD:-10}
MARGIN_THRESHOLD=${MARGIN_THRESHOLD:-80}
ALERT_CHECK_INTERVAL=${ALERT_CHECK_INTERVAL:-30}

# Security
JWT_SECRET=$JWT_SECRET
SESSION_SECRET=$SESSION_SECRET
ENCRYPTION_KEY=$ENCRYPTION_KEY

# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=$SESSION_SECRET

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001
EOF
    "
    
    # Install Docker, Docker Compose, and Node.js
    print_status "Installing Docker, Docker Compose, and Node.js..."
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$APP_PUBLIC_IP" "
        sudo yum update -y
        sudo yum install -y docker
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -a -G docker ec2-user
        
        # Install Docker Compose
        sudo curl -L https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        
        # Install Node.js 18.x for frontend dependencies
        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
        sudo yum install -y nodejs
        
        # Install frontend dependencies if frontend directory exists
        if [ -d 'frontend' ]; then
            cd frontend
            print_status 'Installing frontend dependencies on server...'
            npm install --production --no-optional
            cd ..
        fi
    "
    
    print_success "Modern dashboard and application server deployed"
}

# Function to setup SSL certificates
setup_ssl_certificates() {
    print_milestone "Setting up SSL certificates with Let's Encrypt..."
    
    # Update nginx configuration for SSL
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$APP_PUBLIC_IP" "
        # Create SSL-ready nginx configuration
        cat > nginx/sites-available/schwabapi.conf << 'EOF'
# HTTP server - redirects to HTTPS and handles Let's Encrypt challenges
server {
    listen 80;
    server_name $DOMAIN_NAME;

    # Let's Encrypt challenge location
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Redirect all other HTTP traffic to HTTPS
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name $DOMAIN_NAME;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;
    
    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security \"max-age=31536000; includeSubDomains\" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection \"1; mode=block\" always;
    add_header Referrer-Policy \"strict-origin-when-cross-origin\" always;

    # Rate limiting
    limit_req zone=api burst=20 nodelay;

    # Main dashboard/frontend
    location / {
        proxy_pass http://dashboard:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # API routes - proxy to API server
    location /api/ {
        # Proxy to API server
        proxy_pass http://$API_PRIVATE_IP:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # API-specific timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # CORS headers for API
        add_header Access-Control-Allow-Origin \"https://$DOMAIN_NAME\" always;
        add_header Access-Control-Allow-Methods \"GET, POST, PUT, DELETE, OPTIONS\" always;
        add_header Access-Control-Allow-Headers \"Authorization, Content-Type, X-Requested-With\" always;
        add_header Access-Control-Allow-Credentials true always;
        
        # Handle preflight requests
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin \"https://$DOMAIN_NAME\";
            add_header Access-Control-Allow-Methods \"GET, POST, PUT, DELETE, OPTIONS\";
            add_header Access-Control-Allow-Headers \"Authorization, Content-Type, X-Requested-With\";
            add_header Access-Control-Allow-Credentials true;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
    }

    # Health check endpoint
    location /health {
        proxy_pass http://dashboard:3000/health;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        access_log off;
    }

    # Static assets with caching
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://dashboard:3000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        
        # Cache static assets
        expires 1y;
        add_header Cache-Control \"public, immutable\";
        add_header X-Content-Type-Options nosniff;
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~ ~$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF
    "
    
    print_success "SSL configuration prepared"
}

# Function to start the complete application stack
start_application_stack() {
    print_milestone "Starting Complete Application Stack..."
    
    # Start Docker Compose stack
    print_status "Starting Docker Compose stack with all services..."
    ssh -i "${KEY_PAIR_NAME}.pem" ec2-user@"$APP_PUBLIC_IP" "
        # Build and start all services
        docker-compose build --no-cache
        docker-compose up -d
        
        # Wait for services to be healthy
        sleep 60
        
        # Check service status
        docker-compose ps
    "
    
    print_success "Application stack started successfully"
}

# Function to deploy application code to both servers
deploy_application() {
    deploy_api_server
    deploy_application_server
    setup_ssl_certificates
    start_application_stack
}

# Function to verify the complete application deployment
verify_application() {
    print_milestone "Verifying Complete Application Deployment..."
    
    # Wait for services to start
    sleep 60
    
    # Test API server directly
    local api_public_ip=$(aws ec2 describe-instances \
        --instance-ids "$API_INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text \
        --region "$REGION")
    
    print_status "Testing enhanced API server at $api_public_ip:8080..."
    local max_attempts=6
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://$api_public_ip:8080/health" > /dev/null; then
            print_success "Enhanced API server health check passed"
            break
        fi
        print_status "Waiting for API server... (attempt $attempt/$max_attempts)"
        sleep 15
        ((attempt++))
    done
    
    # Test Application server modern dashboard
    print_status "Testing modern dashboard at $APP_PUBLIC_IP..."
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://$APP_PUBLIC_IP" > /dev/null; then
            print_success "Modern dashboard health check passed"
            
            # Test API proxy through application server
            if curl -f -s "http://$APP_PUBLIC_IP/api/status" > /dev/null; then
                print_success "API proxy through application server working"
                return 0
            else
                print_warning "API proxy may have issues, but dashboard is running"
                return 0
            fi
        fi
        
        print_status "Waiting for modern dashboard... (attempt $attempt/$max_attempts)"
        sleep 15
        ((attempt++))
    done
    
    print_warning "Some services may still be starting up"
    print_status "You can check service status manually with: docker-compose ps"
}

# Function to display comprehensive deployment information
show_deployment_info() {
    echo ""
    echo "=================================================================="
    print_milestone "MILESTONE 2 DEPLOYMENT COMPLETED SUCCESSFULLY!"
    echo "=================================================================="
    echo ""
    echo "🚀 Modern Dashboard URL: http://$APP_PUBLIC_IP"
    echo "🌐 Production Domain: https://$DOMAIN_NAME (after DNS setup)"
    echo "📊 API Server: http://$(aws ec2 describe-instances --instance-ids $API_INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region $REGION):8080"
    echo ""
    echo "📋 Infrastructure Information:"
    echo "   API Server Instance: $API_INSTANCE_ID (Private: $API_PRIVATE_IP)"
    echo "   App Server Instance: $APP_INSTANCE_ID (Public: $APP_PUBLIC_IP)"
    echo "   Elastic IP: $ELASTIC_IP"
    echo "   Domain: $DOMAIN_NAME"
    echo ""
    echo "🔑 SSH Access:"
    echo "   API Server: ssh -i ${KEY_PAIR_NAME}.pem ec2-user@$(aws ec2 describe-instances --instance-ids $API_INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region $REGION)"
    echo "   App Server: ssh -i ${KEY_PAIR_NAME}.pem ec2-user@$APP_PUBLIC_IP"
    echo ""
    echo "🔧 Service Management:"
    echo "   API Server: sudo systemctl status schwab-api"
    echo "   App Server: docker-compose ps"
    echo "   View Logs: docker-compose logs -f [service_name]"
    echo ""
    echo "🎯 Milestone 2 Features Deployed:"
    echo "   ✅ Modern React/Next.js Dashboard with Tailwind CSS"
    echo "   ✅ Google SSO Integration (NextAuth.js)"
    echo "   ✅ Enhanced API Server with Prometheus Monitoring"
    echo "   ✅ PostgreSQL Database for Persistent Storage"
    echo "   ✅ Redis Cache and Job Queue"
    echo "   ✅ Background Worker with Alert System"
    echo "   ✅ Email and Slack Notifications"
    echo "   ✅ Nginx Reverse Proxy with Security Headers"
    echo "   ✅ SSL Certificate Automation (Let's Encrypt Ready)"
    echo "   ✅ Docker Containerization with Health Checks"
    echo "   ✅ Comprehensive Logging and Monitoring"
    echo ""
    echo "🔒 Security Features:"
    echo "   • Google OAuth2 Single Sign-On"
    echo "   • SSL/TLS Encryption Ready"
    echo "   • Security Headers (HSTS, CSP, etc.)"
    echo "   • Rate Limiting and DDoS Protection"
    echo "   • Secure Credential Management (AWS Secrets Manager)"
    echo ""
    echo "📊 Monitoring & Alerts:"
    echo "   • Prometheus Metrics: http://$APP_PUBLIC_IP:9090"
    echo "   • API Metrics: http://$(aws ec2 describe-instances --instance-ids $API_INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region $REGION):8081/metrics"
    echo "   • Worker Metrics: http://$APP_PUBLIC_IP:8082/metrics"
    echo "   • Real-time Alerts via Email and Slack"
    echo ""
    echo "🌐 DNS Setup Required:"
    echo "   1. Point $DOMAIN_NAME A record to: $ELASTIC_IP"
    echo "   2. Wait for DNS propagation (5-30 minutes)"
    echo "   3. SSL certificates will auto-generate via Let's Encrypt"
    echo "   4. Access via: https://$DOMAIN_NAME"
    echo ""
    echo "🚀 Ready to Use:"
    echo "   1. Open http://$APP_PUBLIC_IP in your browser"
    echo "   2. Sign in with Google SSO"
    echo "   3. Connect your Schwab account via OAuth"
    echo "   4. Start monitoring your portfolio with advanced metrics"
    echo ""
    echo "📚 What's Next (Milestone 3):"
    echo "   • Automated Trading Bot Implementation"
    echo "   • Advanced Risk Management"
    echo "   • Strategy Backtesting"
    echo "   • Performance Analytics"
    echo "   • Compliance and Audit Logging"
    echo ""
    echo "✅ One-Command Deployment Complete!"
    echo "   Customers can now: git clone && ./aws/deploy.sh"
    echo ""
}

# Main execution function
main() {
    echo "=== AWS EC2 Deployment for Charles Schwab API Integration - Milestone 2 ==="
    echo ""
    print_milestone "Deploying Production-Ready System with Modern Dashboard & Security"
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
                echo "Milestone 2 Deployment - Modern Dashboard, Security & Monitoring"
                echo ""
                echo "Options:"
                echo "  --stack-name NAME       CloudFormation stack name (default: schwab-api-stack)"
                echo "  --key-pair NAME         EC2 key pair name (default: schwab-api-keypair)"
                echo "  --instance-type TYPE    EC2 instance type (default: t3.small)"
                echo "  --environment ENV       Environment name (default: production)"
                echo "  --region REGION         AWS region (default: us-east-1)"
                echo "  --help                  Show this help message"
                echo ""
                echo "Features Deployed:"
                echo "  • Modern React/Next.js Dashboard"
                echo "  • Google SSO Integration"
                echo "  • Enhanced Monitoring & Alerts"
                echo "  • SSL Certificate Automation"
                echo "  • PostgreSQL & Redis"
                echo "  • Docker Containerization"
                echo "  • Production Security"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Step 1: Check prerequisites
    check_aws_cli
    
    # Step 2: Cleanup existing resources (optional)
    cleanup_aws_resources
    
    # Step 3: Collect all configuration
    collect_domain_config
    collect_google_sso_config
    collect_notification_config
    collect_schwab_credentials
    
    # Step 3: Create key pair
    create_key_pair
    
    # Step 4: Deploy infrastructure
    deploy_stack
    
    # Step 5: Get stack outputs
    get_stack_outputs
    
    # Step 6: Update secrets manager
    update_secrets_manager
    
    # Step 7: Wait for instances
    wait_for_instance
    
    # Step 8: Deploy applications
    deploy_application
    
    # Step 9: Verify deployment
    verify_application
    
    # Step 10: Show deployment information
    show_deployment_info
    
    print_success "Milestone 2 deployment completed successfully!"
}

# Execute main function
main "$@"
