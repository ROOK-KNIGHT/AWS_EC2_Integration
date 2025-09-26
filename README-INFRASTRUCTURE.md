# Charles Schwab API Integration - Infrastructure Guide

## Overview

This document details the AWS infrastructure architecture, dynamic IP configuration, and network topology for the Charles Schwab API integration platform. The infrastructure is designed for high availability, security, and automatic scaling with **zero hardcoded IP addresses**.

## 🏗️ AWS Infrastructure Architecture

### CloudFormation Stack: `schwab-api-stack`

The entire infrastructure is defined as Infrastructure as Code (IaC) using AWS CloudFormation, ensuring consistent and repeatable deployments.

```yaml
# Stack Components
- VPC with public subnet
- 2 EC2 instances (API + Application)
- Elastic IP (preserved across deployments)
- Security Groups with restrictive rules
- IAM roles and policies
- Secrets Manager for credentials
- CloudWatch logging
```

## 🌐 Network Architecture

### VPC Configuration
```
VPC: 10.0.0.0/16
├── Public Subnet: 10.0.1.0/24
│   ├── API Server (private IP: dynamic)
│   └── Application Server (public IP: Elastic IP)
├── Internet Gateway
└── Route Table (public routes)
```

### IP Address Management

#### Dynamic Private IP (API Server)
- **Assignment**: AWS automatically assigns from subnet range
- **Range**: 10.0.1.4 - 10.0.1.254 (dynamic)
- **Retrieval**: Via CloudFormation outputs
- **Usage**: Backend API communication only

#### Elastic IP (Application Server)
- **Assignment**: Static public IP address
- **Preservation**: Maintained across deployments
- **DNS**: Points to domain name
- **Usage**: Public internet access and SSL certificates

### Dynamic IP Discovery Process

#### 1. CloudFormation Output Retrieval
```bash
# Get API server private IP dynamically
API_PRIVATE_IP=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`APIPrivateIP`].OutputValue' \
    --output text)

# Get Application server public IP
APP_PUBLIC_IP=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`AppPublicIP`].OutputValue' \
    --output text)
```

#### 2. Configuration Injection
```bash
# Nginx configuration with dynamic backend
cat > nginx/sites-available/schwabapi.conf << EOF
location /api/ {
    proxy_pass http://$API_PRIVATE_IP:8080;
    # ... other configuration
}
EOF

# Environment variables
cat > .env << EOF
API_BASE_URL=http://$API_PRIVATE_IP:8080
EOF
```

#### 3. Service Discovery
```bash
# Docker Compose environment injection
environment:
  - API_BASE_URL=http://$API_PRIVATE_IP:8080
```

## 🔒 Security Groups

### API Server Security Group (`schwab-api-sg`)
```yaml
Ingress Rules:
  - Port 22 (SSH): 0.0.0.0/0
  - Port 8080 (API): 10.0.0.0/16 (VPC only)

Egress Rules:
  - All traffic: 0.0.0.0/0
```

### Application Server Security Group (`schwab-app-sg`)
```yaml
Ingress Rules:
  - Port 22 (SSH): 0.0.0.0/0
  - Port 80 (HTTP): 0.0.0.0/0
  - Port 443 (HTTPS): 0.0.0.0/0
  - Port 5432 (PostgreSQL): 10.0.0.0/16 (VPC only)

Egress Rules:
  - All traffic: 0.0.0.0/0
```

## 🖥️ EC2 Instance Configuration

### API Server Instance
```yaml
Instance Type: t3.small
AMI: Amazon Linux 2023
Storage: 20GB GP3 EBS
Subnet: Public (with private communication)
Security Group: schwab-api-sg
IAM Role: schwab-api-ec2-role
```

#### User Data Script
```bash
#!/bin/bash
yum update -y
yum install -y python3 python3-pip git htop docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /opt/schwab-api
chown ec2-user:ec2-user /opt/schwab-api

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm
```

### Application Server Instance
```yaml
Instance Type: t3.medium
AMI: Amazon Linux 2023
Storage: 30GB GP3 EBS
Subnet: Public
Security Group: schwab-app-sg
IAM Role: schwab-api-ec2-role
Elastic IP: Associated
```

#### User Data Script
```bash
#!/bin/bash
yum update -y
yum install -y python3 python3-pip git htop nginx docker
systemctl start docker
systemctl enable docker
systemctl enable nginx
usermod -a -G docker ec2-user

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Create application directory
mkdir -p /opt/schwab-app
chown ec2-user:ec2-user /opt/schwab-app
```

## 🔐 IAM Configuration

### EC2 Role Permissions
```yaml
Role Name: schwab-api-ec2-role
Policies:
  - CloudWatchAgentServerPolicy (AWS Managed)
  - SchwabAPIPolicy (Custom)
```

### Custom Policy: SchwabAPIPolicy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:CreateSecret",
        "secretsmanager:UpdateSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:*:*:secret:production/schwab-api/credentials*",
        "arn:aws:secretsmanager:*:*:secret:production/schwab-api/tokens*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams",
        "logs:DescribeLogGroups"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

## 🗄️ AWS Secrets Manager

### Secret Structure: `production/schwab-api/credentials`
```json
{
  "schwab_client_id": "your-schwab-client-id",
  "schwab_client_secret": "your-schwab-client-secret",
  "schwab_callback_url": "https://schwabapi.isaaccmartinez.com/auth/schwab/callback",
  "google_client_id": "your-google-client-id.apps.googleusercontent.com",
  "google_client_secret": "your-google-client-secret",
  "domain_name": "schwabapi.isaaccmartinez.com",
  "admin_email": "admin@imart.com",
  "notification_email": "admin@imart.com",
  "postgres_password": "auto-generated-secure-password",
  "redis_password": "auto-generated-secure-password",
  "jwt_secret": "auto-generated-jwt-secret",
  "session_secret": "auto-generated-session-secret",
  "nextauth_secret": "auto-generated-nextauth-secret",
  "encryption_key": "auto-generated-encryption-key"
}
```

## 🌍 Elastic IP Management

### Elastic IP Preservation Logic

#### Detection Process
```bash
# 1. Check existing CloudFormation stack
EXISTING_EIP=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs[?OutputKey==`ElasticIPAddress`].OutputValue' \
    --output text 2>/dev/null)

# 2. Check DNS resolution
DNS_IP=$(dig +short "$DOMAIN_NAME" @8.8.8.8 2>/dev/null | tail -n1)

# 3. Verify ownership
PRESERVED_EIP_ALLOC_ID=$(aws ec2 describe-addresses \
    --public-ips "$DNS_IP" \
    --query 'Addresses[0].AllocationId' \
    --output text 2>/dev/null)
```

#### CloudFormation Parameters
```yaml
Parameters:
  ElasticIPAllocationId:
    Type: String
    Default: ""
    Description: "Allocation ID of existing Elastic IP to preserve"

Conditions:
  CreateNewElasticIP: !Equals [!Ref ElasticIPAllocationId, ""]

Resources:
  ElasticIP:
    Type: AWS::EC2::EIP
    Condition: CreateNewElasticIP
    Properties:
      Domain: vpc

  ElasticIPAssociation:
    Type: AWS::EC2::EIPAssociation
    Properties:
      AllocationId: !If 
        - CreateNewElasticIP
        - !GetAtt ElasticIP.AllocationId
        - !Ref ElasticIPAllocationId
      InstanceId: !Ref AppInstance
```

### Benefits of Elastic IP Preservation
- ✅ **SSL Certificate Continuity**: No certificate regeneration needed
- ✅ **DNS Stability**: No DNS changes required
- ✅ **Zero Downtime**: Seamless redeployments
- ✅ **Cost Optimization**: No additional IP charges

## 📊 CloudWatch Integration

### Log Groups
```yaml
Log Group: /aws/ec2/production-schwab-api
Retention: 30 days
Streams:
  - API server application logs
  - System logs
  - Docker container logs
```

### Custom Metrics
```python
# API Server Metrics (Prometheus format)
schwab_api_requests_total
schwab_api_request_duration_seconds
schwab_api_active_connections
schwab_api_system_cpu_percent
schwab_api_system_memory_percent
```

## 🔄 Infrastructure Updates

### Stack Updates
```bash
# Update existing stack
aws cloudformation update-stack \
    --stack-name "$STACK_NAME" \
    --template-body file://cloudformation-template.yaml \
    --parameters ParameterKey=ElasticIPAllocationId,ParameterValue=$PRESERVED_EIP_ALLOC_ID \
    --capabilities CAPABILITY_NAMED_IAM
```

### Rolling Updates
- **Zero Downtime**: Elastic IP preserved during updates
- **Blue-Green**: New instances created before old ones terminated
- **Rollback**: CloudFormation stack rollback capability

## 🌐 DNS Configuration

### Domain Setup
```bash
# DNS A Record Configuration
Domain: schwabapi.isaaccmartinez.com
Type: A
Value: [Elastic IP Address]
TTL: 300 (5 minutes)
```

### SSL Certificate Integration
```bash
# Let's Encrypt Certificate
Domain: schwabapi.isaaccmartinez.com
Certificate Path: /etc/letsencrypt/live/schwabapi.isaaccmartinez.com/
Auto-Renewal: Every 12 hours via cron
```

## 🔧 Infrastructure Monitoring

### Health Checks
```yaml
API Server:
  - HTTP health endpoint: :8080/health
  - Prometheus metrics: :8081/metrics
  - System metrics: CPU, Memory, Disk

Application Server:
  - HTTP health endpoint: :80/health
  - Service status: docker-compose ps
  - SSL certificate validity
```

### Automated Monitoring
```bash
# Service monitoring script
#!/bin/bash
# Check API server health
curl -f http://$API_PRIVATE_IP:8080/health

# Check application server health  
curl -f http://$APP_PUBLIC_IP/health

# Check SSL certificate expiry
openssl s_client -connect $DOMAIN_NAME:443 -servername $DOMAIN_NAME 2>/dev/null | openssl x509 -noout -dates
```

## 🚀 Scaling Considerations

### Horizontal Scaling
- **Load Balancer**: Application Load Balancer for multiple app servers
- **Auto Scaling**: Auto Scaling Groups for dynamic capacity
- **Database**: RDS for managed PostgreSQL with read replicas

### Vertical Scaling
- **Instance Types**: Easy upgrade via CloudFormation parameter
- **Storage**: EBS volume expansion without downtime
- **Memory**: Instance type changes for increased capacity

## 🔐 Security Best Practices

### Network Security
- **VPC Isolation**: Private subnets for sensitive services
- **Security Groups**: Principle of least privilege
- **NACLs**: Additional network-level security
- **VPC Flow Logs**: Network traffic monitoring

### Access Control
- **IAM Roles**: No hardcoded credentials
- **Secrets Manager**: Encrypted credential storage
- **SSH Keys**: Unique key pairs per deployment
- **MFA**: Multi-factor authentication for AWS access

### Data Protection
- **Encryption at Rest**: EBS volume encryption
- **Encryption in Transit**: SSL/TLS for all communications
- **Backup Strategy**: Automated snapshots and backups
- **Audit Logging**: CloudTrail for API calls

## 📈 Cost Optimization

### Resource Optimization
- **Instance Sizing**: Right-sized instances for workload
- **Spot Instances**: For non-critical workloads
- **Reserved Instances**: For predictable workloads
- **Storage Optimization**: GP3 volumes for cost efficiency

### Monitoring Costs
- **Cost Explorer**: Track spending by service
- **Budgets**: Set spending alerts
- **Resource Tagging**: Track costs by environment
- **Unused Resources**: Regular cleanup of orphaned resources

## 🔄 Disaster Recovery

### Backup Strategy
- **EBS Snapshots**: Daily automated snapshots
- **Database Backups**: PostgreSQL dumps to S3
- **Configuration Backup**: Infrastructure as Code in Git
- **SSL Certificates**: Backed up to S3

### Recovery Procedures
- **Infrastructure**: Redeploy via CloudFormation
- **Data**: Restore from latest snapshots
- **DNS**: Update A records if needed
- **SSL**: Regenerate certificates if required

This infrastructure design ensures high availability, security, and maintainability while eliminating the complexity of hardcoded IP addresses through dynamic configuration management.
