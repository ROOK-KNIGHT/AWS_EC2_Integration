# Charles Schwab API Integration with AWS EC2

This project provides a complete solution for integrating with the Charles Schwab API and deploying it on AWS EC2. It includes a web interface for trading operations, historical data retrieval, and account management.

## 🚀 Features

- **Charles Schwab API Integration**: Complete OAuth authentication with token management
- **Trading Operations**: Place market orders, limit orders, and view positions
- **Historical Data**: Fetch and analyze historical stock data
- **Account Management**: View positions, balances, and account details
- **Web Interface**: User-friendly web dashboard for all operations
- **AWS Integration**: Secure deployment on EC2 with Secrets Manager integration
- **Multi-Region Support**: Deploy in US, Europe, Asia-Pacific, or Brazil regions
- **Docker Support**: Containerized deployment option
- **Monitoring**: Built-in health checks and logging

## 📋 Prerequisites

Before you begin, ensure you have:

1. **Charles Schwab Developer Account**
   - App Key and App Secret from [Schwab Developer Portal](https://developer.schwab.com/)
   - Approved application for trading access

2. **AWS Account**
   - AWS CLI installed and configured
   - Appropriate IAM permissions for EC2, CloudFormation, and Secrets Manager

3. **Local Development Environment**
   - Python 3.9+ installed
   - Git installed
   - SSH client

## 🛠️ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/ROOK-KNIGHT/AWS_EC2_Integration.git
cd AWS_EC2_Integration
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
# Charles Schwab API Configuration
SCHWAB_APP_KEY=your_schwab_app_key_here
SCHWAB_APP_SECRET=your_schwab_app_secret_here
SCHWAB_REDIRECT_URI=https://127.0.0.1

# AWS Configuration (Choose your preferred region)
AWS_REGION=us-east-1  # US East (N. Virginia)
# AWS_REGION=us-west-2  # US West (Oregon)
# AWS_REGION=eu-west-1  # Europe (Ireland)
# AWS_REGION=ap-southeast-1  # Asia Pacific (Singapore)
# AWS_REGION=sa-east-1  # Brazil - São Paulo

ENVIRONMENT=production
PORT=8080
APP_ENV=production
LOG_LEVEL=INFO
SECRET_KEY=your_flask_secret_key_here
```

### 3. AWS Credentials Setup

You need to configure AWS credentials for deployment. Choose one of these methods:

#### Option A: AWS CLI Configuration (Recommended)
```bash
aws configure
```
Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1` for US East)
- Default output format (`json`)

#### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

#### Option C: IAM Role (if running on EC2)
If deploying from an EC2 instance, attach an IAM role with the necessary permissions.

### 4. Deploy to AWS

#### Create SSH Key Pair
```bash
# Create a new key pair for EC2 access
aws ec2 create-key-pair --key-name schwab-api-keypair --query 'KeyMaterial' --output text > schwab-api-keypair.pem
chmod 400 schwab-api-keypair.pem
```

#### Deploy Infrastructure
```bash
# Make deployment script executable
chmod +x aws/deploy.sh

# Deploy the CloudFormation stack
./aws/deploy.sh
```

The deployment script will:
- Create the CloudFormation stack
- Set up EC2 instance with proper security groups
- Configure AWS Secrets Manager for secure credential storage
- **Automatically upload your Schwab API credentials from .env to AWS Secrets Manager**
- Install Docker and required dependencies
- Output the public IP address for access

### 5. Deploy Application Code

```bash
# SSH into your EC2 instance
ssh -i schwab-api-keypair.pem ec2-user@YOUR_EC2_PUBLIC_IP

# Clone the repository on EC2
git clone https://github.com/ROOK-KNIGHT/AWS_EC2_Integration.git
cd AWS_EC2_Integration

# Deploy using Docker Compose
docker-compose up -d
```

### 6. Access the Application

Open your browser and navigate to:
```
http://YOUR_EC2_PUBLIC_IP:8080
```

## 🌍 Supported AWS Regions

The application supports deployment in the following regions:

| Region Code | Region Name | Location |
|-------------|-------------|----------|
| `us-east-1` | US East (N. Virginia) | United States |
| `us-west-2` | US West (Oregon) | United States |
| `eu-west-1` | Europe (Ireland) | Europe |
| `ap-southeast-1` | Asia Pacific (Singapore) | Asia |
| `sa-east-1` | South America (São Paulo) | **Brazil** |
| `ap-south-1` | Asia Pacific (Mumbai) | India |
| `eu-central-1` | Europe (Frankfurt) | Germany |

To deploy in Brazil, set `AWS_REGION=sa-east-1` in your `.env` file.

## 🔐 Security Configuration

### Environment Variables Protection
- `.env` file is gitignored to prevent credential exposure
- Use `.env.example` as a template for required variables
- Never commit actual API keys or secrets to version control

### AWS Secrets Manager
- API credentials are stored securely in AWS Secrets Manager
- EC2 instance has IAM role-based access to secrets
- Tokens are encrypted at rest and in transit

### Network Security
- Security groups restrict access to necessary ports only
- HTTPS endpoints for secure communication
- SSH access requires key pair authentication

## 🚀 Local Development

For local development without AWS deployment:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the application locally
python3 app.py
```

Access the local application at `http://localhost:8080`

## 📊 API Endpoints

The application provides the following REST API endpoints:

- `GET /` - Web interface
- `GET /api/status` - System health check
- `GET /api/auth/status` - Authentication status
- `POST /api/auth/start` - Start OAuth flow
- `POST /api/auth/callback` - Handle OAuth callback
- `GET /api/positions` - Get current positions
- `GET /api/historical/{symbol}` - Get historical data
- `POST /api/order` - Place trading orders

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SCHWAB_APP_KEY` | Schwab API App Key | - | Yes |
| `SCHWAB_APP_SECRET` | Schwab API App Secret | - | Yes |
| `SCHWAB_REDIRECT_URI` | OAuth redirect URI | `https://127.0.0.1` | No |
| `AWS_REGION` | AWS deployment region | `sa-east-1` | No |
| `ENVIRONMENT` | Environment name | `production` | No |
| `PORT` | Application port | `8080` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |

### CloudFormation Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `KeyPairName` | EC2 Key Pair name | `schwab-api-keypair` |
| `InstanceType` | EC2 instance type | `t3.micro` |
| `Environment` | Environment name | `production` |

## 🐳 Docker Deployment

Alternative deployment using Docker:

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t schwab-api .
docker run -p 8080:8080 --env-file .env schwab-api
```

## 📝 Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify Schwab API credentials in AWS Secrets Manager
   - Check that redirect URI matches your configuration
   - Ensure your Schwab developer application is approved

2. **AWS Deployment Issues**
   - Verify AWS credentials are configured correctly
   - Check IAM permissions for CloudFormation, EC2, and Secrets Manager
   - Ensure the selected region supports all required services

3. **Connection Issues**
   - Verify security group allows inbound traffic on port 8080
   - Check that EC2 instance has a public IP address
   - Ensure the application is running on the EC2 instance

### Logs and Monitoring

```bash
# Check application logs on EC2
sudo journalctl -u schwab-api -f

# Check Docker logs
docker-compose logs -f

# Check CloudWatch logs in AWS Console
# Navigate to CloudWatch > Log Groups > /aws/ec2/production-schwab-api
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and development purposes. Always test thoroughly in a sandbox environment before using with real trading accounts. The authors are not responsible for any financial losses incurred through the use of this software.

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section above
- Review Schwab API documentation at https://developer.schwab.com/

---

**Happy Trading! 📈**
