# Charles Schwab API Integration with AWS EC2

This project provides a complete solution for integrating with the Charles Schwab API and deploying it on AWS EC2. It includes a web interface for trading operations, historical data retrieval, and account management.

## 🚀 Features

- **Charles Schwab API Integration**: Complete integration with authentication, token management, and API calls
- **Trading Operations**: Place market orders, limit orders, stop orders, and more
- **Historical Data**: Fetch and analyze historical stock data
- **Account Management**: View positions, balances, and account details
- **Web Interface**: User-friendly web dashboard for all operations
- **AWS Integration**: Secure deployment on EC2 with Secrets Manager integration
- **Docker Support**: Containerized deployment option
- **Monitoring**: Built-in health checks and logging

## 📋 Prerequisites

Before you begin, ensure you have:

1. **Charles Schwab Developer Account**
   - App Key and App Secret from Schwab Developer Portal
   - Approved application for trading access

2. **AWS Account**
   - AWS CLI installed and configured
   - Appropriate IAM permissions for EC2, CloudFormation, and Secrets Manager

3. **Local Development Environment**
   - Python 3.9+ installed
   - Git installed
   - SSH client

## 🛠️ Project Structure

```
AWS_EC2_Integration/
├── .env                          # Environment variables (your API keys)
├── app.py                        # Main Flask application
├── requirements.txt              # Python dependencies
