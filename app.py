#!/usr/bin/env python3
"""
Main application file for Charles Schwab API Integration
Provides a Flask web interface and API endpoints for trading operations
Enhanced with dashboard features, metrics, alerts, and notifications
"""

import os
import sys
import logging
import json
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

# Add handlers and services directories to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'handlers'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))

# Import our handlers
from connection_manager import ensure_valid_tokens, get_all_positions
from historical_data_handler import HistoricalDataHandler
from order_handler import OrderHandler

# Import services
from metrics_calculator import MetricsCalculator
from alert_manager import AlertManager
from notification_service import NotificationService
from options_service import OptionsService

# Import database models
from database import db, Trade, Position, DailyMetrics, Alert, Watchlist, WatchlistItem, Configuration

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration
database_url = os.getenv('DATABASE_URL', 'sqlite:///trading_dashboard.db')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
log_dir = '/opt/schwab-api/logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'app.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global variables for handlers
data_handler = None
order_handler = None

def get_secrets_from_aws():
    """Get secrets from AWS Secrets Manager if running on EC2"""
    try:
        # Check if we're running on EC2 by trying to get instance metadata
        import requests
        response = requests.get('http://169.254.169.254/latest/meta-data/instance-id', timeout=2)
        if response.status_code == 200:
            logger.info("Running on EC2, attempting to get secrets from AWS Secrets Manager")
            
            # Get secrets from AWS Secrets Manager
            session = boto3.session.Session()
            client = session.client('secretsmanager', region_name=os.getenv('AWS_REGION', 'us-east-1'))
            
            secret_name = f"{os.getenv('ENVIRONMENT', 'production')}/schwab-api/credentials"
            
            try:
                response = client.get_secret_value(SecretId=secret_name)
                secret = json.loads(response['SecretString'])
                
                # Set environment variables from secrets
                os.environ['SCHWAB_APP_KEY'] = secret['SCHWAB_APP_KEY']
                os.environ['SCHWAB_APP_SECRET'] = secret['SCHWAB_APP_SECRET']
                os.environ['SCHWAB_REDIRECT_URI'] = secret.get('SCHWAB_REDIRECT_URI', 'https://127.0.0.1')
                
                logger.info("Successfully loaded secrets from AWS Secrets Manager")
                return True
            except ClientError as e:
                logger.error(f"Error getting secrets from AWS: {e}")
                return False
    except Exception as e:
        logger.info("Not running on EC2 or unable to access metadata service, using local .env file")
        return False

def initialize_handlers():
    """Initialize the data and order handlers"""
    global data_handler, order_handler
    
    try:
        # Try to get secrets from AWS first
        get_secrets_from_aws()
        
        # Initialize handlers without triggering authentication
        data_handler = HistoricalDataHandler()
        # Don't initialize order handler yet - it will trigger authentication
        # order_handler = OrderHandler()
        
        logger.info("Handlers initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing handlers: {e}")
        return False

def get_order_handler():
    """Lazy initialization of order handler"""
    global order_handler
    if order_handler is None:
        try:
            order_handler = OrderHandler()
        except Exception as e:
            logger.error(f"Error initializing order handler: {e}")
            return None
    return order_handler

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Charles Schwab API Integration</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; text-align: center; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .status { padding: 10px; border-radius: 5px; margin: 10px 0; }
        .status.success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .status.info { background-color: #d1ecf1; color: #0c5460; border: 1px solid #bee5eb; }
        button { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin: 5px; }
        button:hover { background-color: #0056b3; }
        input, select { padding: 8px; margin: 5px; border: 1px solid #ddd; border-radius: 3px; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .form-group { margin: 10px 0; }
        label { display: inline-block; width: 120px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Charles Schwab API Integration</h1>
        
        <div class="section">
            <h2>System Status</h2>
            <div id="status" class="status info">Checking system status...</div>
            <button onclick="checkStatus()">Refresh Status</button>
        </div>
        
        <div class="section">
            <h2>Authentication</h2>
            <div id="auth-status" class="status info">Checking authentication status...</div>
            <button onclick="checkAuthStatus()">Check Auth Status</button>
            <button onclick="startAuthentication()">Authenticate with Charles Schwab</button>
            
            <div style="margin-top: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background-color: #f8f9fa;">
                <h4>Manual Authentication Callback</h4>
                <p><small>If you were redirected to a localhost URL after authentication, paste the full URL here:</small></p>
                <div class="form-group">
                    <input type="text" id="callback-url" placeholder="https://127.0.0.1/?code=..." style="width: 70%; margin-right: 10px;">
                    <button onclick="processCallback()">Process Authentication</button>
                </div>
                <div id="callback-result"></div>
            </div>
            
            <div style="margin-top: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background-color: #fff3cd;">
                <h4>Manual Token Entry</h4>
                <p><small>If you already have saved Schwab API tokens, you can enter them directly here:</small></p>
                <div class="form-group">
                    <label>Access Token:</label>
                    <input type="text" id="access-token" placeholder="Enter your access token" style="width: 100%; margin-bottom: 10px;">
                </div>
                <div class="form-group">
                    <label>Refresh Token:</label>
                    <input type="text" id="refresh-token" placeholder="Enter your refresh token" style="width: 100%; margin-bottom: 10px;">
                </div>
                <div class="form-group">
                    <label>Expires At:</label>
                    <input type="datetime-local" id="expires-at" style="width: 100%; margin-bottom: 10px;">
                </div>
                <button onclick="uploadTokens()">Upload Tokens</button>
                <div id="token-upload-result"></div>
            </div>
        </div>
        
        <div class="section">
            <h2>Account Positions</h2>
            <button onclick="getPositions()">Get Current Positions</button>
            <div id="positions"></div>
        </div>
        
        <div class="section">
            <h2>Historical Data</h2>
            <div class="form-group">
                <label>Symbol:</label>
                <input type="text" id="symbol" placeholder="AAPL" value="AAPL">
            </div>
            <button onclick="getHistoricalData()">Get Historical Data</button>
            <div id="historical-data"></div>
        </div>
        
        <div class="section">
            <h2>Place Order</h2>
            <div class="form-group">
                <label>Symbol:</label>
                <input type="text" id="order-symbol" placeholder="AAPL">
            </div>
            <div class="form-group">
                <label>Action:</label>
                <select id="order-action">
                    <option value="BUY">BUY</option>
                    <option value="SELL">SELL</option>
                    <option value="SELL_SHORT">SELL_SHORT</option>
                    <option value="BUY_TO_COVER">BUY_TO_COVER</option>
                </select>
            </div>
            <div class="form-group">
                <label>Order Type:</label>
                <select id="order-type">
                    <option value="market">Market</option>
                    <option value="limit">Limit</option>
                </select>
            </div>
            <div class="form-group">
                <label>Shares:</label>
                <input type="number" id="order-shares" placeholder="100">
            </div>
            <div class="form-group">
                <label>Price:</label>
                <input type="number" id="order-price" placeholder="150.00" step="0.01">
            </div>
            <button onclick="placeOrder()">Place Order</button>
            <div id="order-result"></div>
        </div>
    </div>

    <script>
        function checkStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    if (data.status === 'healthy') {
                        statusDiv.className = 'status success';
                        statusDiv.innerHTML = `
                            <strong>System Status: Healthy</strong><br>
                            Handlers Initialized: ${data.handlers_initialized}<br>
                            Last Check: ${new Date().toLocaleString()}
                        `;
                    } else {
                        statusDiv.className = 'status error';
                        statusDiv.innerHTML = `
                            <strong>System Status: Error</strong><br>
                            Error: ${data.error}<br>
                            Last Check: ${new Date().toLocaleString()}
                        `;
                    }
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = `<strong>Error:</strong> ${error}`;
                    document.getElementById('status').className = 'status error';
                });
        }

        function getPositions() {
            fetch('/api/positions')
                .then(response => response.json())
                .then(data => {
                    const positionsDiv = document.getElementById('positions');
                    if (data.error) {
                        positionsDiv.innerHTML = `<div class="status error">Error: ${data.error}</div>`;
                    } else {
                        let html = '<table><tr><th>Account</th><th>Symbol</th><th>Quantity</th><th>Market Value</th><th>Unrealized P&L</th></tr>';
                        for (const [account, positions] of Object.entries(data)) {
                            for (const pos of positions) {
                                html += `<tr>
                                    <td>${account}</td>
                                    <td>${pos.symbol}</td>
                                    <td>${pos.quantity}</td>
                                    <td>$${pos.market_value?.toFixed(2) || 'N/A'}</td>
                                    <td>$${pos.unrealized_pl?.toFixed(2) || 'N/A'}</td>
                                </tr>`;
                            }
                        }
                        html += '</table>';
                        positionsDiv.innerHTML = html;
                    }
                })
                .catch(error => {
                    document.getElementById('positions').innerHTML = `<div class="status error">Error: ${error}</div>`;
                });
        }

        function getHistoricalData() {
            const symbol = document.getElementById('symbol').value;
            if (!symbol) {
                alert('Please enter a symbol');
                return;
            }
            
            fetch(`/api/historical/${symbol}`)
                .then(response => response.json())
                .then(data => {
                    const dataDiv = document.getElementById('historical-data');
                    if (data.error) {
                        dataDiv.innerHTML = `<div class="status error">Error: ${data.error}</div>`;
                    } else {
                        // Get the latest candle for current price
                        const latestCandle = data.candles && data.candles.length > 0 ? 
                            data.candles[data.candles.length - 1] : null;
                        
                        const currentPrice = latestCandle ? latestCandle.close : 'N/A';
                        const previousClose = data.previousClose || (latestCandle ? latestCandle.open : 'N/A');
                        
                        // Calculate change if we have both values
                        let changeInfo = '';
                        if (currentPrice !== 'N/A' && previousClose !== 'N/A' && 
                            typeof currentPrice === 'number' && typeof previousClose === 'number') {
                            const change = currentPrice - previousClose;
                            const changePercent = ((change / previousClose) * 100).toFixed(2);
                            const changeColor = change >= 0 ? 'green' : 'red';
                            changeInfo = `<br>Change: <span style="color: ${changeColor}">$${change.toFixed(2)} (${changePercent}%)</span>`;
                        }
                        
                        dataDiv.innerHTML = `
                            <div class="status success">
                                <strong>Historical Data for ${data.symbol}</strong><br>
                                Records: ${data.candles?.length || 0}<br>
                                Current Price: $${typeof currentPrice === 'number' ? currentPrice.toFixed(2) : currentPrice}<br>
                                Previous Close: $${typeof previousClose === 'number' ? previousClose.toFixed(2) : previousClose}${changeInfo}
                                ${data.previousCloseDate ? `<br>Previous Close Date: ${data.previousCloseDate}` : ''}
                            </div>
                        `;
                    }
                })
                .catch(error => {
                    document.getElementById('historical-data').innerHTML = `<div class="status error">Error: ${error}</div>`;
                });
        }

        function placeOrder() {
            const orderData = {
                symbol: document.getElementById('order-symbol').value,
                action: document.getElementById('order-action').value,
                order_type: document.getElementById('order-type').value,
                shares: parseInt(document.getElementById('order-shares').value),
                price: parseFloat(document.getElementById('order-price').value)
            };

            if (!orderData.symbol || !orderData.shares) {
                alert('Please fill in symbol and shares');
                return;
            }

            fetch('/api/order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(orderData)
            })
            .then(response => response.json())
            .then(data => {
                const resultDiv = document.getElementById('order-result');
                if (data.status === 'submitted') {
                    resultDiv.innerHTML = `
                        <div class="status success">
                            <strong>Order Submitted Successfully</strong><br>
                            Order ID: ${data.order_id}<br>
                            Symbol: ${data.symbol}<br>
                            Action: ${data.action_type}<br>
                            Shares: ${data.shares}<br>
                            ${data.fill_price ? `Price: $${data.fill_price}` : ''}
                        </div>
                    `;
                } else {
                    resultDiv.innerHTML = `<div class="status error">Order Failed: ${data.reason || data.error}</div>`;
                }
            })
            .catch(error => {
                document.getElementById('order-result').innerHTML = `<div class="status error">Error: ${error}</div>`;
            });
        }

        function checkAuthStatus() {
            fetch('/api/auth/status')
                .then(response => response.json())
                .then(data => {
                    const authStatusDiv = document.getElementById('auth-status');
                    if (data.authenticated) {
                        authStatusDiv.className = 'status success';
                        authStatusDiv.innerHTML = `
                            <strong>Authentication Status: Authenticated</strong><br>
                            Expires: ${new Date(data.expires_at).toLocaleString()}<br>
                            Last Check: ${new Date().toLocaleString()}
                        `;
                    } else {
                        authStatusDiv.className = 'status error';
                        authStatusDiv.innerHTML = `
                            <strong>Authentication Status: Not Authenticated</strong><br>
                            Error: ${data.error}<br>
                            Last Check: ${new Date().toLocaleString()}
                        `;
                    }
                })
                .catch(error => {
                    document.getElementById('auth-status').innerHTML = `<strong>Error:</strong> ${error}`;
                    document.getElementById('auth-status').className = 'status error';
                });
        }

        function startAuthentication() {
            fetch('/api/auth/start')
                .then(response => response.json())
                .then(data => {
                    if (data.auth_url) {
                        // Open authentication URL in a new window
                        window.open(data.auth_url, '_blank');
                        
                        // Show instructions
                        const authStatusDiv = document.getElementById('auth-status');
                        authStatusDiv.className = 'status info';
                        authStatusDiv.innerHTML = `
                            <strong>Authentication Started</strong><br>
                            ${data.message}<br>
                            <em>${data.instructions}</em><br>
                            <small>A new window should have opened. Complete the authentication there and return here.</small>
                        `;
                    } else {
                        document.getElementById('auth-status').innerHTML = `<strong>Error:</strong> ${data.error}`;
                        document.getElementById('auth-status').className = 'status error';
                    }
                })
                .catch(error => {
                    document.getElementById('auth-status').innerHTML = `<strong>Error:</strong> ${error}`;
                    document.getElementById('auth-status').className = 'status error';
                });
        }

        function processCallback() {
            const callbackUrl = document.getElementById('callback-url').value.trim();
            const resultDiv = document.getElementById('callback-result');
            
            if (!callbackUrl) {
                resultDiv.innerHTML = '<div class="status error">Please enter the callback URL</div>';
                return;
            }
            
            // Extract the code from the URL
            try {
                const url = new URL(callbackUrl);
                const code = url.searchParams.get('code');
                
                if (!code) {
                    resultDiv.innerHTML = '<div class="status error">No authorization code found in URL</div>';
                    return;
                }
                
                resultDiv.innerHTML = '<div class="status info">Processing authentication...</div>';
                
                // Send the code to our callback endpoint
                fetch('/api/auth/callback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ code: code })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        resultDiv.innerHTML = `
                            <div class="status success">
                                <strong>Authentication Successful!</strong><br>
                                ${data.message}<br>
                                Expires: ${new Date(data.expires_at).toLocaleString()}
                            </div>
                        `;
                        // Clear the input field
                        document.getElementById('callback-url').value = '';
                        // Refresh auth status
                        checkAuthStatus();
                    } else {
                        resultDiv.innerHTML = `<div class="status error">Authentication Failed: ${data.error}</div>`;
                    }
                })
                .catch(error => {
                    resultDiv.innerHTML = `<div class="status error">Error: ${error}</div>`;
                });
                
            } catch (error) {
                resultDiv.innerHTML = '<div class="status error">Invalid URL format</div>';
            }
        }

        function uploadTokens() {
            const accessToken = document.getElementById('access-token').value.trim();
            const refreshToken = document.getElementById('refresh-token').value.trim();
            const expiresAt = document.getElementById('expires-at').value;
            const resultDiv = document.getElementById('token-upload-result');
            
            if (!accessToken || !refreshToken || !expiresAt) {
                resultDiv.innerHTML = '<div class="status error">Please fill in all token fields</div>';
                return;
            }
            
            resultDiv.innerHTML = '<div class="status info">Uploading tokens...</div>';
            
            // Convert datetime-local to ISO string
            const expiresAtISO = new Date(expiresAt).toISOString();
            
            fetch('/api/auth/upload-tokens', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    access_token: accessToken,
                    refresh_token: refreshToken,
                    expires_at: expiresAtISO
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    resultDiv.innerHTML = `
                        <div class="status success">
                            <strong>Tokens Uploaded Successfully!</strong><br>
                            ${data.message}<br>
                            Expires: ${new Date(data.expires_at).toLocaleString()}
                        </div>
                    `;
                    // Clear the input fields
                    document.getElementById('access-token').value = '';
                    document.getElementById('refresh-token').value = '';
                    document.getElementById('expires-at').value = '';
                    // Refresh auth status
                    checkAuthStatus();
                } else {
                    resultDiv.innerHTML = `<div class="status error">Token Upload Failed: ${data.error}</div>`;
                }
            })
            .catch(error => {
                resultDiv.innerHTML = `<div class="status error">Error: ${error}</div>`;
            });
        }

        // Check status and auth status on page load
        checkStatus();
        checkAuthStatus();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main web interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    try:
        # Check if handlers are initialized
        handlers_ok = data_handler is not None
        
        # Check if we have credentials available (don't trigger authentication)
        has_credentials = (os.getenv('SCHWAB_APP_KEY') is not None and 
                          os.getenv('SCHWAB_APP_SECRET') is not None)
        
        # Check if we have existing tokens (don't create new ones)
        tokens_exist = os.path.exists(os.getenv('SCHWAB_TOKEN_FILE', 'cs_tokens.json'))
        
        return jsonify({
            'status': 'healthy' if handlers_ok and has_credentials else 'warning',
            'handlers_initialized': handlers_ok,
            'credentials_available': has_credentials,
            'tokens_exist': tokens_exist,
            'aws_secrets_loaded': 'Running on EC2' if has_credentials else 'Using local .env',
            'message': 'System ready. Authentication required for trading operations.' if has_credentials else 'Missing credentials',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/positions')
def api_positions():
    """Get current positions"""
    try:
        positions = get_all_positions()
        if positions is None:
            return jsonify({'error': 'Failed to get positions'}), 500
        return jsonify(positions)
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/historical/<symbol>')
def api_historical(symbol):
    """Get historical data for a symbol"""
    try:
        if not data_handler:
            return jsonify({'error': 'Data handler not initialized'}), 500
        
        # Get 30 days of daily data
        data = data_handler.fetch_historical_data(
            symbol=symbol.upper(),
            periodType="month",
            period=1,
            frequencyType="daily",
            freq=1,
            needExtendedHoursData=False
        )
        
        if not data:
            return jsonify({'error': 'No data available'}), 404
        
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting historical data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/order', methods=['POST'])
def api_order():
    """Place an order"""
    try:
        order_handler = get_order_handler()
        if not order_handler:
            return jsonify({'error': 'Order handler not initialized'}), 500
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        symbol = data.get('symbol', '').upper()
        action = data.get('action', '').upper()
        order_type = data.get('order_type', 'market').lower()
        shares = data.get('shares')
        price = data.get('price')
        
        if not symbol or not action or not shares:
            return jsonify({'error': 'Missing required fields: symbol, action, shares'}), 400
        
        # Place the order
        if order_type == 'market':
            result = order_handler.place_market_order(action, symbol, shares, price)
        elif order_type == 'limit':
            if not price:
                return jsonify({'error': 'Price required for limit orders'}), 400
            result = order_handler.place_limit_order(action, symbol, shares, price)
        else:
            return jsonify({'error': 'Invalid order type'}), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/start')
def start_auth():
    """Start the authentication process"""
    try:
        from connection_manager import get_auth_url
        auth_url = get_auth_url()
        return jsonify({
            'auth_url': auth_url,
            'message': 'Visit this URL to authenticate with Charles Schwab',
            'instructions': 'After authentication, you will be redirected back to this server'
        })
    except Exception as e:
        logger.error(f"Error starting auth: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/callback')
def oauth_callback():
    """Handle OAuth callback from Charles Schwab"""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({'error': 'No authorization code received'}), 400
        
        # Import here to avoid circular imports
        from connection_manager import get_tokens
        
        # Exchange code for tokens
        tokens = get_tokens(code)
        if tokens:
            return jsonify({
                'status': 'success',
                'message': 'Authentication successful! You can now use the API.',
                'expires_at': tokens.get('expires_at')
            })
        else:
            return jsonify({'error': 'Failed to exchange code for tokens'}), 500
            
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/callback', methods=['POST'])
def manual_auth_callback():
    """Handle manual authentication callback with authorization code"""
    try:
        data = request.get_json()
        if not data or 'code' not in data:
            return jsonify({'error': 'No authorization code provided'}), 400
        
        code = data['code']
        
        # Import here to avoid circular imports
        from connection_manager import get_tokens
        
        # Exchange code for tokens
        tokens = get_tokens(code)
        if tokens:
            return jsonify({
                'status': 'success',
                'message': 'Authentication successful! You can now use the API.',
                'expires_at': tokens.get('expires_at')
            })
        else:
            return jsonify({'error': 'Failed to exchange code for tokens'}), 500
            
    except Exception as e:
        logger.error(f"Error in manual auth callback: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/status')
def auth_status():
    """Check authentication status"""
    try:
        from connection_manager import load_tokens
        tokens = load_tokens()
        
        if tokens:
            expires_at = tokens.get('expires_at')
            if expires_at:
                from datetime import datetime
                try:
                    expires_datetime = datetime.fromisoformat(expires_at)
                    is_expired = datetime.now() >= expires_datetime
                    return jsonify({
                        'authenticated': not is_expired,
                        'expires_at': expires_at,
                        'expired': is_expired
                    })
                except ValueError:
                    return jsonify({'authenticated': False, 'error': 'Invalid token format'})
            else:
                return jsonify({'authenticated': False, 'error': 'No expiration time found'})
        else:
            return jsonify({'authenticated': False, 'error': 'No tokens found'})
            
    except Exception as e:
        logger.error(f"Error checking auth status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/upload-tokens', methods=['POST'])
def upload_tokens():
    """Handle manual token upload"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        access_token = data.get('access_token', '').strip()
        refresh_token = data.get('refresh_token', '').strip()
        expires_at = data.get('expires_at', '').strip()
        
        if not access_token or not refresh_token or not expires_at:
            return jsonify({'error': 'Missing required fields: access_token, refresh_token, expires_at'}), 400
        
        # Validate the expires_at format
        try:
            from datetime import datetime
            expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            
            # Check if the token is already expired
            if expires_datetime <= datetime.now():
                return jsonify({'error': 'Token expiration time is in the past'}), 400
                
        except ValueError as e:
            return jsonify({'error': f'Invalid expires_at format: {str(e)}'}), 400
        
        # Import here to avoid circular imports
        from connection_manager import save_tokens
        
        # Create token dictionary
        tokens = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at,
            'token_type': 'Bearer'
        }
        
        # Save the tokens
        if save_tokens(tokens):
            logger.info("Manual tokens uploaded successfully")
            return jsonify({
                'status': 'success',
                'message': 'Tokens uploaded and saved successfully! You can now use the API.',
                'expires_at': expires_at
            })
        else:
            return jsonify({'error': 'Failed to save tokens'}), 500
            
    except Exception as e:
        logger.error(f"Error uploading tokens: {e}")
        return jsonify({'error': str(e)}), 500

# Dashboard API Endpoints

@app.route('/api/dashboard/metrics')
def dashboard_metrics():
    """Get dashboard metrics"""
    try:
        days = request.args.get('days', 30, type=int)
        metrics_calc = MetricsCalculator()
        
        # Get comprehensive performance summary
        summary = metrics_calc.get_performance_summary(days)
        
        return jsonify(summary)
    except Exception as e:
        logger.error(f"Error getting dashboard metrics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/portfolio')
def dashboard_portfolio():
    """Get portfolio metrics"""
    try:
        days = request.args.get('days', 30, type=int)
        metrics_calc = MetricsCalculator()
        
        portfolio_metrics = metrics_calc.calculate_portfolio_metrics(days)
        position_metrics = metrics_calc.calculate_position_metrics()
        
        return jsonify({
            'portfolio_metrics': portfolio_metrics,
            'positions': position_metrics
        })
    except Exception as e:
        logger.error(f"Error getting portfolio data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/options')
def dashboard_options():
    """Get options metrics and data"""
    try:
        options_service = OptionsService()
        metrics_calc = MetricsCalculator()
        
        # Get options metrics
        options_metrics = metrics_calc.calculate_options_metrics()
        portfolio_greeks = options_service.calculate_portfolio_greeks()
        
        return jsonify({
            'options_metrics': options_metrics,
            'portfolio_greeks': portfolio_greeks
        })
    except Exception as e:
        logger.error(f"Error getting options data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/options/chain/<symbol>')
def options_chain(symbol):
    """Get options chain for a symbol"""
    try:
        options_service = OptionsService()
        
        # Get query parameters
        contract_type = request.args.get('contractType', 'ALL')
        strike_count = request.args.get('strikeCount', 10, type=int)
        range_type = request.args.get('range', 'ALL')
        
        chain_data = options_service.fetch_options_chain(
            symbol=symbol.upper(),
            contract_type=contract_type,
            strike_count=strike_count,
            range_type=range_type
        )
        
        return jsonify(chain_data)
    except Exception as e:
        logger.error(f"Error getting options chain: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/options/opportunities')
def options_opportunities():
    """Find options trading opportunities"""
    try:
        options_service = OptionsService()
        
        # Get search criteria from query parameters
        criteria = {
            'min_iv_rank': request.args.get('min_iv_rank', 70, type=int),
            'max_days_to_expiration': request.args.get('max_dte', 45, type=int),
            'min_volume': request.args.get('min_volume', 100, type=int),
            'option_type': request.args.get('option_type', 'ALL'),
            'moneyness': request.args.get('moneyness', 'ALL')
        }
        
        opportunities = options_service.find_option_opportunities(criteria)
        
        return jsonify({
            'opportunities': opportunities,
            'criteria': criteria,
            'count': len(opportunities)
        })
    except Exception as e:
        logger.error(f"Error finding options opportunities: {e}")
        return jsonify({'error': str(e)}), 500

# Alerts API Endpoints

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts"""
    try:
        alert_manager = AlertManager()
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        alerts = alert_manager.get_alerts(active_only=active_only)
        
        return jsonify({
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts', methods=['POST'])
def create_alert():
    """Create a new alert"""
    try:
        alert_manager = AlertManager()
        alert_data = request.get_json()
        
        if not alert_data:
            return jsonify({'error': 'No alert data provided'}), 400
        
        result = alert_manager.create_alert(alert_data)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/<int:alert_id>', methods=['PUT'])
def update_alert(alert_id):
    """Update an alert"""
    try:
        alert_manager = AlertManager()
        update_data = request.get_json()
        
        if not update_data:
            return jsonify({'error': 'No update data provided'}), 400
        
        result = alert_manager.update_alert(alert_id, update_data)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error updating alert: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    """Delete an alert"""
    try:
        alert_manager = AlertManager()
        result = alert_manager.delete_alert(alert_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error deleting alert: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/<int:alert_id>/test', methods=['POST'])
def test_alert(alert_id):
    """Test an alert"""
    try:
        alert_manager = AlertManager()
        result = alert_manager.test_alert(alert_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing alert: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/<int:alert_id>/reset', methods=['POST'])
def reset_alert(alert_id):
    """Reset a triggered alert"""
    try:
        alert_manager = AlertManager()
        result = alert_manager.reset_alert(alert_id)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error resetting alert: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/history')
def alert_history():
    """Get alert history"""
    try:
        alert_manager = AlertManager()
        days = request.args.get('days', 7, type=int)
        
        history = alert_manager.get_alert_history(days)
        
        return jsonify({
            'history': history,
            'days': days,
            'count': len(history)
        })
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        return jsonify({'error': str(e)}), 500

# Notifications API Endpoints

@app.route('/api/notifications/status')
def notification_status():
    """Get notification service status"""
    try:
        notification_service = NotificationService()
        status = notification_service.get_notification_status()
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting notification status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/test', methods=['POST'])
def test_notifications():
    """Test all notification channels"""
    try:
        notification_service = NotificationService()
        results = notification_service.test_notifications()
        
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error testing notifications: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/history')
def notification_history():
    """Get notification history"""
    try:
        notification_service = NotificationService()
        days = request.args.get('days', 7, type=int)
        notification_type = request.args.get('type')
        
        history = notification_service.get_notification_history(days, notification_type)
        
        return jsonify({
            'history': history,
            'days': days,
            'type': notification_type,
            'count': len(history)
        })
    except Exception as e:
        logger.error(f"Error getting notification history: {e}")
        return jsonify({'error': str(e)}), 500

# Watchlist API Endpoints

@app.route('/api/watchlists', methods=['GET'])
def get_watchlists():
    """Get all watchlists"""
    try:
        watchlists = db.session.query(Watchlist).filter(Watchlist.is_active == True).all()
        
        return jsonify({
            'watchlists': [wl.to_dict() for wl in watchlists],
            'count': len(watchlists)
        })
    except Exception as e:
        logger.error(f"Error getting watchlists: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlists', methods=['POST'])
def create_watchlist():
    """Create a new watchlist"""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({'error': 'Watchlist name is required'}), 400
        
        watchlist = Watchlist(
            name=data['name'],
            description=data.get('description', '')
        )
        
        db.session.add(watchlist)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'watchlist': watchlist.to_dict()
        }), 201
    except Exception as e:
        logger.error(f"Error creating watchlist: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlists/<int:watchlist_id>/items', methods=['POST'])
def add_watchlist_item(watchlist_id):
    """Add item to watchlist"""
    try:
        data = request.get_json()
        if not data or 'symbol' not in data:
            return jsonify({'error': 'Symbol is required'}), 400
        
        # Check if watchlist exists
        watchlist = db.session.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
        if not watchlist:
            return jsonify({'error': 'Watchlist not found'}), 404
        
        # Check if item already exists
        existing = db.session.query(WatchlistItem).filter(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.symbol == data['symbol'].upper()
        ).first()
        
        if existing:
            return jsonify({'error': 'Symbol already in watchlist'}), 400
        
        item = WatchlistItem(
            watchlist_id=watchlist_id,
            symbol=data['symbol'].upper(),
            notes=data.get('notes', ''),
            target_price=data.get('target_price'),
            stop_loss=data.get('stop_loss')
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'item': item.to_dict()
        }), 201
    except Exception as e:
        logger.error(f"Error adding watchlist item: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# WebSocket Events for Real-time Updates

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info('Client connected')
    emit('status', {'message': 'Connected to trading dashboard'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info('Client disconnected')

@socketio.on('subscribe_metrics')
def handle_subscribe_metrics():
    """Subscribe to real-time metrics updates"""
    try:
        metrics_calc = MetricsCalculator()
        summary = metrics_calc.get_performance_summary(1)  # Today's metrics
        emit('metrics_update', summary)
    except Exception as e:
        logger.error(f"Error sending metrics update: {e}")
        emit('error', {'message': str(e)})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def initialize_database():
    """Initialize database tables and default configuration"""
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            logger.info("Database tables created/verified")
            
            # Add default configuration if not exists
            default_configs = [
                ('dashboard_refresh_interval', '30', 'int', 'Dashboard refresh interval in seconds'),
                ('alert_check_interval', '30', 'int', 'Alert check interval in seconds'),
                ('max_daily_alerts', '50', 'int', 'Maximum alerts per day'),
                ('default_risk_free_rate', '0.05', 'float', 'Default risk-free rate for options calculations'),
                ('notification_settings', '{"email": true, "telegram": false, "slack": false}', 'json', 'Default notification channel settings'),
                ('dashboard_theme', 'light', 'string', 'Dashboard theme (light/dark)'),
                ('timezone', 'America/New_York', 'string', 'Default timezone for the application')
            ]
            
            for key, value, data_type, description in default_configs:
                existing = db.session.query(Configuration).filter(Configuration.key == key).first()
                if not existing:
                    config = Configuration(
                        key=key,
                        value=value,
                        data_type=data_type,
                        description=description
                    )
                    db.session.add(config)
            
            db.session.commit()
            logger.info("Database initialization complete")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return False
    
    return True

if __name__ == '__main__':
    # Initialize database
    if not initialize_database():
        logger.error("Failed to initialize database, exiting")
        sys.exit(1)
    
    # Initialize handlers
    if not initialize_handlers():
        logger.error("Failed to initialize handlers, exiting")
        sys.exit(1)
    
    # Create necessary directories in the correct location
    os.makedirs('/opt/schwab-api/logs', exist_ok=True)
    os.makedirs('/opt/schwab-api/data', exist_ok=True)
    os.makedirs('/opt/schwab-api/tokens', exist_ok=True)
    
    # Start the Flask app
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('APP_ENV', 'production') != 'production'
    
    logger.info(f"Starting Charles Schwab Trading Dashboard on port {port}")
    
    if debug:
        app.run(host='0.0.0.0', port=port, debug=debug)
    else:
        # Use SocketIO for production with real-time features
        socketio.run(app, host='0.0.0.0', port=port, debug=debug)
