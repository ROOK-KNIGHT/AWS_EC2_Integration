#!/bin/bash

# Deploy application to EC2 instance
# This script uploads the application code and starts the services

set -e

# Configuration
INSTANCE_IP=""
KEY_FILE=""
APP_DIR="/opt/schwab-api"
LOCAL_DIR="."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    echo "Usage: $0 --ip <instance-ip> --key <key-file> [OPTIONS]"
    echo ""
    echo "Required:"
    echo "  --ip IP_ADDRESS     Public IP address of the EC2 instance"
    echo "  --key KEY_FILE      Path to the SSH private key file (.pem)"
    echo ""
    echo "Options:"
    echo "  --app-dir DIR       Application directory on EC2 (default: /opt/schwab-api)"
    echo "  --local-dir DIR     Local directory to deploy (default: current directory)"
    echo "  --help              Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --ip 54.123.45.67 --key schwab-api-keypair.pem"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ip)
            INSTANCE_IP="$2"
            shift 2
            ;;
        --key)
            KEY_FILE="$2"
            shift 2
            ;;
        --app-dir)
            APP_DIR="$2"
            shift 2
            ;;
        --local-dir)
            LOCAL_DIR="$2"
            shift 2
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate required parameters
if [[ -z "$INSTANCE_IP" || -z "$KEY_FILE" ]]; then
    print_error "Missing required parameters"
    show_usage
    exit 1
fi

# Check if key file exists
if [[ ! -f "$KEY_FILE" ]]; then
    print_error "Key file not found: $KEY_FILE"
    exit 1
fi

# Check key file permissions
if [[ "$(stat -c %a "$KEY_FILE")" != "400" ]]; then
    print_warning "Key file permissions are not 400, fixing..."
    chmod 400 "$KEY_FILE"
fi

print_status "Starting deployment to EC2 instance: $INSTANCE_IP"

# Test SSH connection
print_status "Testing SSH connection..."
if ! ssh -i "$KEY_FILE" -o ConnectTimeout=10 -o StrictHostKeyChecking=no ec2-user@"$INSTANCE_IP" "echo 'SSH connection successful'" > /dev/null 2>&1; then
    print_error "Cannot connect to EC2 instance. Please check IP address and key file."
    exit 1
fi
print_success "SSH connection successful"

# Create application directory
print_status "Creating application directory..."
ssh -i "$KEY_FILE" ec2-user@"$INSTANCE_IP" "sudo mkdir -p $APP_DIR && sudo chown ec2-user:ec2-user $APP_DIR"

# Create necessary subdirectories
ssh -i "$KEY_FILE" ec2-user@"$INSTANCE_IP" "mkdir -p $APP_DIR/{logs,data,tokens}"

# Upload application files
print_status "Uploading application files..."
rsync -avz --progress -e "ssh -i $KEY_FILE -o StrictHostKeyChecking=no" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='logs/' \
    --exclude='data/' \
    --exclude='tokens/' \
    --exclude='*.pem' \
    "$LOCAL_DIR/" ec2-user@"$INSTANCE_IP":"$APP_DIR/"

print_success "Application files uploaded"

# Upload environment file separately (if it exists)
if [[ -f ".env" ]]; then
    print_status "Uploading environment file..."
    scp -i "$KEY_FILE" .env ec2-user@"$INSTANCE_IP":"$APP_DIR/"
    print_success "Environment file uploaded"
else
    print_warning "No .env file found locally"
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
ssh -i "$KEY_FILE" ec2-user@"$INSTANCE_IP" "cd $APP_DIR && python3 -m pip install --user -r requirements.txt"
print_success "Dependencies installed"

# Create systemd service file
print_status "Creating systemd service..."
ssh -i "$KEY_FILE" ec2-user@"$INSTANCE_IP" "sudo tee /etc/systemd/system/schwab-api.service > /dev/null << 'EOF'
[Unit]
Description=Charles Schwab API Integration
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$APP_DIR
Environment=PATH=/home/ec2-user/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/usr/bin/python3 $APP_DIR/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

# Reload systemd and start service
print_status "Starting application service..."
ssh -i "$KEY_FILE" ec2-user@"$INSTANCE_IP" "
    sudo systemctl daemon-reload
    sudo systemctl enable schwab-api
    sudo systemctl restart schwab-api
"

# Wait a moment for service to start
sleep 5

# Check service status
print_status "Checking service status..."
if ssh -i "$KEY_FILE" ec2-user@"$INSTANCE_IP" "sudo systemctl is-active --quiet schwab-api"; then
    print_success "Service is running"
else
    print_error "Service failed to start"
    print_status "Checking service logs..."
    ssh -i "$KEY_FILE" ec2-user@"$INSTANCE_IP" "sudo journalctl -u schwab-api --no-pager -n 20"
    exit 1
fi

# Test application health
print_status "Testing application health..."
sleep 10  # Give the app time to fully start

if ssh -i "$KEY_FILE" ec2-user@"$INSTANCE_IP" "curl -f http://localhost:8080/health" > /dev/null 2>&1; then
    print_success "Application health check passed"
else
    print_warning "Application health check failed, but service is running"
    print_status "You may need to check the application logs"
fi

# Show deployment information
echo ""
print_success "Deployment completed successfully!"
echo ""
echo "=== DEPLOYMENT INFORMATION ==="
echo "Instance IP: $INSTANCE_IP"
echo "Application Directory: $APP_DIR"
echo "Service Name: schwab-api"
echo ""
echo "=== USEFUL COMMANDS ==="
echo "SSH to instance:"
echo "  ssh -i $KEY_FILE ec2-user@$INSTANCE_IP"
echo ""
echo "Check service status:"
echo "  sudo systemctl status schwab-api"
echo ""
echo "View service logs:"
echo "  sudo journalctl -u schwab-api -f"
echo ""
echo "Restart service:"
echo "  sudo systemctl restart schwab-api"
echo ""
echo "Access web interface:"
echo "  http://$INSTANCE_IP:8080"
echo ""
echo "Test API health:"
echo "  curl http://$INSTANCE_IP:8080/health"
echo ""

print_success "Deployment process completed!"
