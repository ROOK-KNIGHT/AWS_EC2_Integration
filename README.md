# Charles Schwab API Integration on AWS EC2

A complete Flask web application for Charles Schwab API integration, deployed automatically on AWS EC2 with one command.

## 🚀 Quick Start

Deploy the entire application to AWS EC2 with a single command:

```bash
git clone https://github.com/ROOK-KNIGHT/AWS_EC2_Integration.git && cd AWS_EC2_Integration && ./aws/deploy.sh
```

That's it! The script will:
- Deploy AWS infrastructure (EC2, IAM, Secrets Manager)
- Upload and configure the application
- Start the web service
- Provide you with the application URL

## 📋 Prerequisites

Before running the deployment, ensure you have:

1. **AWS CLI installed and configured**
   ```bash
   aws configure
   ```
   You'll need:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (recommend: `us-east-1`)

2. **Required AWS permissions** for your IAM user:
   - EC2 (create instances, key pairs, security groups)
   - CloudFormation (create/update stacks)
   - IAM (create roles and policies)
   - Secrets Manager (create/manage secrets)

3. **Charles Schwab Developer Account**
   - Register at [Charles Schwab Developer Portal](https://developer.schwab.com/)
   - Create an app to get your Client ID and Client Secret

## 🏗️ What Gets Deployed

The deployment script creates:

### AWS Infrastructure
- **EC2 Instance** (t3.small) running Amazon Linux 2023
- **Security Group** allowing HTTP (port 8080) and SSH access
- **IAM Role** with permissions for Secrets Manager
- **Secrets Manager Secret** for storing API credentials
- **SSH Key Pair** for secure instance access

### Application Stack
- **Flask Web Application** with comprehensive UI
- **Python Dependencies** automatically installed
- **Systemd Service** for automatic startup and management
- **Health Monitoring** and verification

## 🌐 Application Features

Once deployed, your application includes:

- **OAuth 2.0 Authentication** with Charles Schwab
- **Account Information** viewing
- **Portfolio Positions** display
- **Historical Data** retrieval
- **Order Placement** interface
- **Automatic Token Management** with refresh
- **Secure Credential Storage** via AWS Secrets Manager

## 📖 Usage Instructions

### 1. Deploy the Application
```bash
./aws/deploy.sh
```

### 2. Configure API Credentials
After deployment, you'll need to add your Schwab API credentials:

1. Go to AWS Secrets Manager in the console
2. Find the secret named `production/schwab-api/credentials`
3. Update it with your credentials:
   ```json
   {
     "client_id": "your_schwab_client_id",
     "client_secret": "your_schwab_client_secret"
   }
   ```

### 3. Access Your Application
Open the provided URL in your browser (e.g., `http://3.95.18.79:8080`) and:
1. Click "Authenticate with Charles Schwab"
2. Complete the OAuth flow
3. Start using the trading interface

## 🔧 Management Commands

### Check Application Status
```bash
ssh -i schwab-api-keypair.pem ec2-user@[YOUR_IP]
sudo systemctl status schwab-api
```

### View Application Logs
```bash
sudo journalctl -u schwab-api -f
```

### Restart Application
```bash
sudo systemctl restart schwab-api
```

## 🛠️ Customization Options

The deployment script supports several options:

```bash
./aws/deploy.sh [OPTIONS]

Options:
  --stack-name NAME       CloudFormation stack name (default: schwab-api-stack)
  --key-pair NAME         EC2 key pair name (default: schwab-api-keypair)
  --instance-type TYPE    EC2 instance type (default: t3.small)
  --environment ENV       Environment name (default: production)
  --region REGION         AWS region (default: us-east-1)
  --help                  Show help message
```

Example with custom options:
```bash
./aws/deploy.sh --instance-type t3.medium --region us-west-2 --environment staging
```

## 📁 Project Structure

```
AWS_EC2_Integration/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── aws/
│   ├── deploy.sh                   # Complete deployment script
│   └── cloudformation-template.yaml # AWS infrastructure template
├── handlers/
│   ├── connection_manager.py       # API connection management
│   ├── fetch_data.py              # Data retrieval functions
│   ├── historical_data_handler.py # Historical data processing
│   └── order_handler.py           # Order placement logic
└── README.md                      # This file
```

## 🔒 Security Features

- **IMDSv2 Support** for secure EC2 metadata access
- **AWS Secrets Manager** for credential storage
- **IAM Roles** with least-privilege permissions
- **Security Groups** with minimal required access
- **HTTPS Redirect URIs** for OAuth flow

## 🚨 Troubleshooting

### Common Issues

**1. AWS CLI not configured**
```bash
aws configure
```

**2. Insufficient AWS permissions**
- Ensure your IAM user has the required permissions listed above

**3. Application not starting**
```bash
ssh -i schwab-api-keypair.pem ec2-user@[YOUR_IP]
sudo journalctl -u schwab-api --no-pager -n 50
```

**4. OAuth redirect issues**
- Ensure your Schwab app's redirect URI is set to `https://127.0.0.1`

### Getting Help

1. Check the application logs on the EC2 instance
2. Verify your Schwab API credentials in Secrets Manager
3. Ensure your Schwab developer app is properly configured

## 💰 Cost Estimation

Running this application on AWS typically costs:
- **EC2 t3.small**: ~$15-20/month
- **Secrets Manager**: ~$0.40/month
- **Data transfer**: Minimal for typical usage

Total estimated cost: **~$16-21/month**

## 🔄 Updates and Maintenance

To update the application:
1. Pull the latest changes: `git pull origin main`
2. Re-run the deployment: `./aws/deploy.sh`

The script will update the existing infrastructure and application code.

## 📜 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Ready to start trading with Charles Schwab on AWS? Run the deployment command and you'll be up and running in minutes!**
