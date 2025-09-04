#connection_manager.py

import base64
import requests
import webbrowser
import json
import urllib.parse
import os
from datetime import timedelta, datetime
import time
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

# Check if running on EC2
def is_running_on_ec2():
    """Check if we're running on EC2 by trying to get instance metadata"""
    try:
        import requests
        # Try IMDSv2 first (with token)
        try:
            token_response = requests.put(
                'http://169.254.169.254/latest/api/token',
                headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
                timeout=2
            )
            if token_response.status_code == 200:
                token = token_response.text
                response = requests.get(
                    'http://169.254.169.254/latest/meta-data/instance-id',
                    headers={'X-aws-ec2-metadata-token': token},
                    timeout=2
                )
                return response.status_code == 200
        except:
            pass
        
        # Fallback to IMDSv1
        response = requests.get('http://169.254.169.254/latest/meta-data/instance-id', timeout=2)
        return response.status_code == 200
    except:
        return False

# Load secrets from AWS Secrets Manager if on EC2
def load_secrets_from_aws():
    """Load secrets from AWS Secrets Manager and set environment variables"""
    try:
        session = boto3.session.Session()
        client = session.client('secretsmanager', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        secret_name = f"{os.getenv('ENVIRONMENT', 'production')}/schwab-api/credentials"
        
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        
        # Set environment variables from secrets (using correct field names)
        os.environ['SCHWAB_APP_KEY'] = secret['client_id']
        os.environ['SCHWAB_APP_SECRET'] = secret['client_secret']
        os.environ['SCHWAB_REDIRECT_URI'] = secret.get('redirect_uri', 'https://127.0.0.1')
        
        print("Successfully loaded secrets from AWS Secrets Manager")
        return True
    except Exception as e:
        print(f"Error loading secrets from AWS: {e}")
        return False

# Load API credentials from environment variables
def load_api_keys():
    """Load API keys from environment variables"""
    try:
        # If running on EC2 and no env vars set, try to load from AWS Secrets Manager
        if is_running_on_ec2() and not os.getenv('SCHWAB_APP_KEY'):
            load_secrets_from_aws()
        
        app_key = os.getenv('SCHWAB_APP_KEY')
        app_secret = os.getenv('SCHWAB_APP_SECRET')
        
        if not app_key or not app_secret:
            raise ValueError("SCHWAB_APP_KEY and SCHWAB_APP_SECRET must be set in environment variables")
        
        return app_key, app_secret
    except Exception as e:
        print(f"Error loading API keys from environment: {e}")
        raise

# Global variables for keys (loaded lazily)
APP_KEY = None
APP_SECRET = None
REDIRECT_URI = None
AUTH_URL = None
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"

def get_api_keys():
    """Get API keys, loading them if not already loaded"""
    global APP_KEY, APP_SECRET
    if APP_KEY is None or APP_SECRET is None:
        APP_KEY, APP_SECRET = load_api_keys()
    return APP_KEY, APP_SECRET

# Configuration - Update redirect URI for EC2
def get_redirect_uri():
    """Get the appropriate redirect URI based on environment"""
    # Always use localhost for callback since that's what's typically configured in Schwab API settings
    # The web interface will handle manual callback processing
    return os.getenv('SCHWAB_REDIRECT_URI', "https://127.0.0.1")

def get_auth_url():
    """Get the authorization URL, loading keys if needed"""
    global AUTH_URL, REDIRECT_URI
    if AUTH_URL is None:
        app_key, _ = get_api_keys()
        if REDIRECT_URI is None:
            REDIRECT_URI = get_redirect_uri()
        AUTH_URL = f"https://api.schwabapi.com/v1/oauth/authorize?response_type=code&client_id={app_key}&redirect_uri={REDIRECT_URI}&scope=readonly"
    return AUTH_URL

# AWS Secrets Manager integration
def save_tokens(tokens):
    """Save tokens to AWS Secrets Manager if on EC2, otherwise local file"""
    # Calculate and save the expiration time as a string
    expires_at = datetime.now() + timedelta(seconds=int(tokens['expires_in']))
    tokens['expires_at'] = expires_at.isoformat()  # Store it as an ISO string
    
    if is_running_on_ec2():
        # Save to AWS Secrets Manager only
        session = boto3.session.Session()
        client = session.client('secretsmanager', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        secret_name = f"{os.getenv('ENVIRONMENT', 'production')}/schwab-api/tokens"
        
        try:
            # Try to update existing secret
            client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(tokens)
            )
            print("Tokens updated in AWS Secrets Manager")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Create new secret if it doesn't exist
                client.create_secret(
                    Name=secret_name,
                    SecretString=json.dumps(tokens),
                    Description="Charles Schwab API tokens"
                )
                print("Tokens created in AWS Secrets Manager")
            else:
                raise
    else:
        # Save to local file for development
        _save_tokens_local(tokens)

def _save_tokens_local(tokens):
    """Save tokens to local file (for local development)"""
    # Use a fixed local filename instead of environment variable
    token_file = "cs_tokens.json"
    with open(token_file, 'w') as f:
        json.dump(tokens, f)

def load_tokens():
    """Load tokens from AWS Secrets Manager if on EC2, otherwise local file"""
    if is_running_on_ec2():
        try:
            # Load from AWS Secrets Manager only
            session = boto3.session.Session()
            client = session.client('secretsmanager', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            
            secret_name = f"{os.getenv('ENVIRONMENT', 'production')}/schwab-api/tokens"
            
            response = client.get_secret_value(SecretId=secret_name)
            tokens = json.loads(response['SecretString'])
            print("Tokens loaded from AWS Secrets Manager")
            return tokens
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print("No tokens found in AWS Secrets Manager")
                return None
            else:
                print(f"Error loading tokens from AWS Secrets Manager: {e}")
                return None
        except Exception as e:
            print(f"Error loading tokens from AWS Secrets Manager: {e}")
            return None
    else:
        # Load from local file for development (use fixed filename)
        token_file = "cs_tokens.json"
        if os.path.exists(token_file):
            with open(token_file, 'r') as f:
                return json.load(f)
        return None

def get_authorization_code():
    print("Manual authentication required. Go to the following URL to authenticate:")
    print(AUTH_URL)
    webbrowser.open(AUTH_URL)
    
    returned_url = input("Paste the full returned URL here as soon as you get it: ")
    
    # Extract the authorization code from the returned URL
    parsed_url = urllib.parse.urlparse(returned_url)
    code = urllib.parse.parse_qs(parsed_url.query).get('code', [None])[0]
    
    if not code:
        raise ValueError("Failed to extract code from the returned URL")
    
    return code


def get_tokens(code):
    print("Exchanging authorization code for tokens...")
    app_key, app_secret = get_api_keys()
    credentials = f"{app_key}:{app_secret}"
    base64_credentials = base64.b64encode(credentials.encode()).decode("utf-8")

    headers = {
        "Authorization": f"Basic {base64_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    global REDIRECT_URI
    if REDIRECT_URI is None:
        REDIRECT_URI = get_redirect_uri()
    
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    
    token_response = requests.post(TOKEN_URL, headers=headers, data=payload)
    if token_response.status_code == 200:
        tokens = token_response.json()
        save_tokens(tokens)
        return tokens
    else:
        print("Failed to get tokens")
        print("Status Code:", token_response.status_code)
        print("Response:", token_response.text)
        return None

def refresh_tokens(refresh_token):
    print("Refreshing access token...")
    app_key, app_secret = get_api_keys()
    credentials = f"{app_key}:{app_secret}"
    base64_credentials = base64.b64encode(credentials.encode()).decode("utf-8")

    headers = {
        "Authorization": f"Basic {base64_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    refresh_response = requests.post(TOKEN_URL, headers=headers, data=payload)
    
    if refresh_response.status_code == 200:
        new_tokens = refresh_response.json()
        save_tokens(new_tokens)
        return new_tokens
    else:
        print("Failed to refresh tokens")
        print("Status Code:", refresh_response.status_code)
        print("Response:", refresh_response.text)
        return None


# Modify ensure_valid_tokens to check expiration time
def ensure_valid_tokens():
    tokens = load_tokens()
    if tokens:
        expires_at = tokens.get('expires_at')
        
        # Check if 'expires_at' exists and is a valid string
        if expires_at:
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                print("Invalid 'expires_at' format in tokens. Re-authentication required.")
                return None  # Return None instead of forcing interactive auth
        else:
            print("'expires_at' missing from tokens. Re-authentication required.")
            return None  # Return None instead of forcing interactive auth

        if tokens:
            refresh_token = tokens.get("refresh_token")
            # Check if access token is expired or about to expire (within a buffer, e.g., 2 minutes)
            if datetime.now() >= expires_at - timedelta(minutes=2):
                print("Access token is about to expire or has expired, attempting to refresh...")
                new_tokens = refresh_tokens(refresh_token)
                if new_tokens:
                    return new_tokens  # Token successfully refreshed
                else:
                    print("Failed to refresh tokens. Please re-authenticate via web interface.")
                    return None  # Return None instead of forcing interactive auth
            else:
                return tokens  # Access token is still valid

    # If no tokens found, return None - authentication should be done via web interface
    print("No tokens found. Please authenticate via the web interface.")
    return None


def get_account_numbers(access_token):
    url = "https://api.schwabapi.com/trader/v1/accounts/accountNumbers"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    retries = 5
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)  # 10 seconds timeout
            response.raise_for_status()  # Raise error for bad status codes
            return response.json()
        except requests.exceptions.ReadTimeout:
            print(f"Request timed out on attempt {attempt + 1}/{retries}. Retrying...")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}, attempt {attempt + 1}/{retries}")
        time.sleep(2 ** attempt)  # Exponential backoff

    raise Exception(f"Failed to fetch account numbers after {retries} attempts")

def get_account_details(access_token, account_number, field):
    #print(f"DEBUG : Fetching account details for account {account_number}...")
    url = f"https://api.schwabapi.com/trader/v1/accounts/{account_number}?fields={field}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        print(f"Rate limit exceeded. Retry after {retry_after} seconds.")
        return None
    else:
        print(f"Failed to get account details\nStatus Code: {response.status_code}\nResponse: {response.text}")
        return None

def get_positions(access_token, account_number):
    """Get current positions for the specified account"""
    url = f"https://api.schwabapi.com/trader/v1/accounts/{account_number}/positions"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                positions = response.json()
                # Format the positions data
                formatted_positions = []
                for pos in positions.get('positions', []):
                    formatted_positions.append({
                        'symbol': pos.get('symbol'),
                        'quantity': pos.get('quantity'),
                        'cost_basis': pos.get('costBasis'),
                        'market_value': pos.get('marketValue'),
                        'unrealized_pl': pos.get('unrealizedPL'),
                        'unrealized_pl_percent': pos.get('unrealizedPLPercent')
                    })
                return formatted_positions
            elif response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                print(f"Rate limit exceeded. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
            else:
                print(f"Failed to get positions. Status Code: {response.status_code}")
                print(f"Response: {response.text}")
                time.sleep(2 ** attempt)  # Exponential backoff
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return None

def get_all_positions():
    """Get positions for all accounts"""
    try:
        # Ensure we have valid tokens
        tokens = ensure_valid_tokens()
        if not tokens:
            print("Failed to get valid tokens")
            return None
            
        access_token = tokens['access_token']
        
        # Get accounts with positions
        url = "https://api.schwabapi.com/trader/v1/accounts?fields=positions"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to get accounts. Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
        accounts = response.json()
        all_positions = {}
        
        for account in accounts:
            securities_account = account.get('securitiesAccount', {})
            account_number = securities_account.get('accountNumber')
            positions = securities_account.get('positions', [])
            
            if account_number and positions:
                formatted_positions = []
                for pos in positions:
                    instrument = pos.get('instrument', {})
                    formatted_positions.append({
                        'symbol': instrument.get('symbol'),
                        'quantity': pos.get('longQuantity', 0) - pos.get('shortQuantity', 0),
                        'cost_basis': pos.get('averagePrice', 0) * pos.get('longQuantity', 0),
                        'market_value': pos.get('marketValue', 0),
                        'unrealized_pl': pos.get('longOpenProfitLoss', 0) + pos.get('shortOpenProfitLoss', 0),
                        'unrealized_pl_percent': (pos.get('currentDayProfitLossPercentage', 0))
                    })
                if formatted_positions:
                    all_positions[account_number] = formatted_positions
                    
        return all_positions
    except Exception as e:
        print(f"Error getting all positions: {str(e)}")
        return None
