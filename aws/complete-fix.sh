#!/bin/bash

# Complete Fix Script for Charles Schwab API Trading Dashboard
# This script uploads all required files and fixes the deployment

set -e

# Configuration
APP_PUBLIC_IP="3.220.143.63"
API_PUBLIC_IP="34.235.125.106"
KEY_PAIR_NAME="schwab-api-keypair"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Function to check if SSH key exists
check_ssh_key() {
    if [ ! -f "${KEY_PAIR_NAME}.pem" ]; then
        print_error "SSH key file ${KEY_PAIR_NAME}.pem not found!"
        print_error "Please ensure the key file is in the current directory."
        exit 1
    fi
    chmod 400 "${KEY_PAIR_NAME}.pem"
}

# Function to upload all required files
upload_all_files() {
    print_status "Uploading all required files to application server..."
    
    # Upload Dockerfiles and worker script
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no \
        Dockerfile.dashboard Dockerfile.worker worker.py requirements.txt \
        ec2-user@"$APP_PUBLIC_IP":~/
    
    # Upload application directories
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no -r \
        frontend/ services/ models/ handlers/ \
        ec2-user@"$APP_PUBLIC_IP":~/
    
    # Upload additional files
    scp -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no \
        app.py init_db.py .env \
        ec2-user@"$APP_PUBLIC_IP":~/
    
    print_success "All files uploaded successfully"
}

# Function to create a simple working Docker setup
create_simple_setup() {
    print_status "Creating simplified Docker setup..."
    
    ssh -i "${KEY_PAIR_NAME}.pem" -o StrictHostKeyChecking=no ec2-user@"$APP_PUBLIC_IP" "
        # Stop any running containers
        docker-compose down || true
        docker system prune -f || true
        
        # Create necessary directories
        mkdir -p logs/{nginx,dashboard,worker} database/init
        
        # Create a simplified docker-compose.yml that works
        cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: schwab-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: schwab_trading
      POSTGRES_USER: schwab_user
      POSTGRES_PASSWORD: secure_password
    ports:
      - \"5432:5432\"
    volumes:
