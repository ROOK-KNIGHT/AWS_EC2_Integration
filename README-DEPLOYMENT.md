# Charles Schwab API Integration - Deployment Guide

## Overview

This project implements a **dual-instance AWS deployment architecture** with a single-script deployment system that creates a production-ready Charles Schwab API integration platform with Google SSO authentication, modern React dashboard, and comprehensive monitoring.

## 🏗️ Dual-Instance Architecture

### Instance 1: API Server (`t3.small`)
- **Role**: Backend API processing and data handling
- **Location**: Private subnet with VPC-only access
- **Services**: 
  - Flask API server (port 8080)
  - Prometheus metrics (port 8081)
  - SQLite database for local caching
  - Enhanced monitoring and logging
- **IP Assignment**: **Dynamic private IP** (retrieved automatically)
- **Access**: SSH via public IP, API access via private IP through Application Server

### Instance 2: Application Server (`t3.medium`)
- **Role**: Frontend hosting, reverse proxy, and SSL termination
- **Location**: Public subnet with internet access
- **Services**:
  - Nginx reverse proxy (ports 80/443)
  - React/Next.js dashboard (port 3000)
  - PostgreSQL database (port 5432)
  - Redis cache (port 6379)
  - Background worker with alerts
  - SSL certificate management
- **IP Assignment**: **Elastic IP** (preserved across deployments)
- **Access**: Public internet access with domain name

## 🚀 Single-Script Deployment

### Quick Start
```bash
git clone https://github.com/ROOK-KNIGHT/AWS_EC2_Integration.git
cd AWS_EC2_Integration/aws
./deploy.sh
```

### What the Script Does

#### Phase 1: Infrastructure Setup
1. **AWS Resource Cleanup** (optional)
   - Preserves existing Elastic IP if found
   - Safely removes old instances and resources
   - Maintains DNS continuity

2. **Configuration Collection**
   - Domain configuration (default: schwabapi.isaaccmartinez.com)
   - Google SSO credentials (OAuth2)
   - Schwab API credentials
   - Notification settings (email, Slack, Telegram)
   - Trading alert thresholds

3. **CloudFormation Deployment**
   - Creates VPC with public subnet
   - Deploys dual EC2 instances
   - Sets up security groups
   - Configures IAM roles and policies
   - Associates/creates Elastic IP

#### Phase 2: Application Deployment

4. **API Server Setup**
   - Uploads Python application code
   - Installs dependencies and monitoring tools
   - Initializes SQLite database
   - Starts enhanced API service with systemd
   - Configures Prometheus metrics

5. **Application Server Setup**
   - Uploads Docker Compose configuration
   - Builds and starts containerized services
   - Configures nginx with **dynamic API IP injection**
   - Sets up SSL certificates with Let's Encrypt
   - Initializes PostgreSQL and Redis

#### Phase 3: SSL and Production Setup

6. **Dynamic IP Configuration**
   - Retrieves API server private IP automatically
   - Updates nginx configuration with correct backend
   - No hardcoded IP addresses anywhere
   - Handles IP changes across deployments

7. **SSL Certificate Generation**
   - Waits for DNS propagation
   - Generates Let's Encrypt certificates
   - Configures HTTPS with security headers
   - Sets up automatic certificate renewal

## 📁 File Structure and Locations

### Local Development Files
```
AWS_EC2_Integration/
├── aws/
│   ├── deploy.sh                    # Main deployment script
│   ├── cloudformation-template.yaml # Infrastructure as Code
│   └── schwab-api-keypair-*.pem    # SSH keys (generated)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Login.js            # Google SSO login
│   │   │   ├── ProtectedRoute.js   # Route protection
│   │   │   └── Sidebar.js          # Navigation with logout
│   │   ├── contexts/
│   │   │   └── AuthContext.js      # Authentication state
│   │   └── App.js                  # Main application
│   ├── package.json                # Frontend dependencies
│   └── Dockerfile                  # Frontend container
├── app.py                          # Main Flask API
├── requirements.txt                # Python dependencies
├── docker-compose.app.yml          # Application services
├── nginx/
│   ├── nginx.conf                  # Main nginx config
│   └── sites-available/
│       └── schwabapi.conf          # Site-specific config
└── handlers/, models/, services/   # API modules
```

### Deployed File Locations

#### API Server (`/opt/schwab-api/`)
```
/opt/schwab-api/
├── app.py                          # Main Flask application
├── enhanced_app.py                 # Monitoring wrapper
├── requirements.txt                # Python dependencies
├── init_db.py                      # Database initialization
├── handlers/                       # Request handlers
├── models/                         # Data models
├── services/                       # Business logic
├── config/
│   └── monitoring.py               # Prometheus setup
└── logs/                           # Application logs
```

#### Application Server (`~/`)
```
/home/ec2-user/
├── docker-compose.yml              # Service orchestration
├── .env                            # Environment variables
├── nginx/
│   ├── nginx.conf                  # Nginx configuration
│   ├── sites-available/
│   │   └── schwabapi.conf          # Site config (dynamic IP)
│   ├── ssl/                        # SSL certificates
│   └── webroot/                    # ACME challenge
├── frontend/                       # React application
├── database/
│   └── init/                       # Database initialization
├── worker/                         # Background worker
└── logs/                           # Service logs
```

## 🔄 Dynamic IP Management

### The Problem Solved
- **Previous Issue**: Hardcoded IP addresses caused deployment failures
- **Solution**: Dynamic IP retrieval and injection

### How It Works

1. **IP Discovery**
   ```bash
   API_PRIVATE_IP=$(aws cloudformation describe-stacks \
       --stack-name "$STACK_NAME" \
       --query 'Stacks[0].Outputs[?OutputKey==`APIPrivateIP`].OutputValue' \
       --output text)
   ```

2. **Configuration Injection**
   ```bash
   # Nginx configuration with dynamic IP
   proxy_pass http://$API_PRIVATE_IP:8080;
   ```

3. **Environment Variables**
   ```bash
   API_BASE_URL=http://$API_PRIVATE_IP:8080
   ```

### Benefits
- ✅ No hardcoded IP addresses
- ✅ Works across deployments
- ✅ Handles instance replacements
- ✅ Automatic configuration updates

## 🔐 Security Features

### Authentication
- **Google SSO**: OAuth2 integration with NextAuth.js
- **Session Management**: Secure JWT tokens
- **Route Protection**: Protected routes for authenticated users

### Network Security
- **VPC Isolation**: Private subnet for API server
- **Security Groups**: Restrictive firewall rules
- **SSL/TLS**: Let's Encrypt certificates with auto-renewal
- **Security Headers**: HSTS, CSP, XSS protection

### Credential Management
- **AWS Secrets Manager**: Encrypted credential storage
- **Environment Variables**: Secure configuration
- **IAM Roles**: Least privilege access

## 📊 Monitoring and Alerts

### Metrics Collection
- **Prometheus**: API server metrics (port 8081)
- **Worker Metrics**: Background job monitoring (port 8082)
- **System Metrics**: CPU, memory, disk usage

### Alert System
- **Email Notifications**: SMTP-based alerts
- **Slack Integration**: Webhook notifications
- **Telegram Bots**: Real-time messaging
- **Trading Alerts**: Loss limits, volatility spikes

### Log Management
- **Structured Logging**: JSON format with timestamps
- **CloudWatch Integration**: Centralized log collection
- **Service Logs**: Separate logs per service

## 🔧 Deployment Commands

### Full Deployment
```bash
./deploy.sh
```

### Deployment with Options
```bash
./deploy.sh --stack-name my-stack --instance-type t3.medium --region us-west-2
```

### Available Options
- `--stack-name`: CloudFormation stack name
- `--key-pair`: EC2 key pair name
- `--instance-type`: EC2 instance type
- `--environment`: Environment (dev/staging/production)
- `--region`: AWS region
- `--help`: Show help information

## 🔄 Redeployment Process

### Preserving Elastic IP
The deployment script automatically:
1. Detects existing Elastic IP
2. Preserves IP across deployments
3. Maintains DNS configuration
4. Ensures SSL certificate continuity

### Update Deployment
```bash
# Pull latest changes
git pull origin main

# Redeploy (preserves IP)
./deploy.sh
```

## 🐛 Troubleshooting

### Common Issues

#### SSH Connection Timeout
```bash
# Check instance status
aws ec2 describe-instances --instance-ids i-xxxxx

# Verify security groups
aws ec2 describe-security-groups --group-ids sg-xxxxx
```

#### Service Not Starting
```bash
# Check service status
ssh -i keypair.pem ec2-user@ip "docker-compose ps"

# View logs
ssh -i keypair.pem ec2-user@ip "docker-compose logs service-name"
```

#### SSL Certificate Issues
```bash
# Check certificate status
ssh -i keypair.pem ec2-user@ip "docker-compose exec certbot certbot certificates"

# Regenerate certificates
ssh -i keypair.pem ec2-user@ip "docker-compose run --rm certbot certonly --webroot ..."
```

### Log Locations
- **API Server**: `/opt/schwab-api/logs/`
- **Application Services**: `~/logs/`
- **System Logs**: `/var/log/`

## 🎯 Next Steps

After successful deployment:

1. **Configure Google OAuth**
   - Update redirect URIs in Google Console
   - Test SSO login functionality

2. **Set up Schwab API**
   - Configure callback URLs
   - Test API connectivity

3. **Monitor System**
   - Check Prometheus metrics
   - Verify alert notifications
   - Review log outputs

4. **Production Hardening**
   - Review security settings
   - Configure backup strategies
   - Set up monitoring dashboards

## 📞 Support

For deployment issues:
1. Check the deployment logs
2. Verify AWS credentials and permissions
3. Ensure domain DNS is properly configured
4. Review security group settings

The deployment script provides comprehensive error handling and status reporting throughout the process.
