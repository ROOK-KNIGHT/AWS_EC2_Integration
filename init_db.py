#!/usr/bin/env python3
"""
Database initialization script
Creates all tables and sets up initial configuration
"""

import os
import sys
from datetime import datetime

# Add models directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'models'))

from flask import Flask
from database import db, Configuration

def create_app():
    """Create Flask app for database initialization"""
    app = Flask(__name__)
    
    # Database configuration
    database_url = os.getenv('DATABASE_URL', 'sqlite:///trading_dashboard.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    return app

def initialize_database():
    """Initialize database with tables and default configuration"""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        
        # Create all tables
        db.create_all()
        
        print("Database tables created successfully!")
        
        # Add default configuration
        default_configs = [
            {
                'key': 'dashboard_refresh_interval',
                'value': '30',
                'data_type': 'int',
                'description': 'Dashboard refresh interval in seconds'
            },
            {
                'key': 'alert_check_interval',
                'value': '30',
                'data_type': 'int',
                'description': 'Alert check interval in seconds'
            },
            {
                'key': 'max_daily_alerts',
                'value': '50',
                'data_type': 'int',
                'description': 'Maximum alerts per day'
            },
            {
                'key': 'default_risk_free_rate',
                'value': '0.05',
                'data_type': 'float',
                'description': 'Default risk-free rate for options calculations'
            },
            {
                'key': 'notification_settings',
                'value': '{"email": true, "telegram": false, "slack": false}',
                'data_type': 'json',
                'description': 'Default notification channel settings'
            },
            {
                'key': 'dashboard_theme',
                'value': 'light',
                'data_type': 'string',
                'description': 'Dashboard theme (light/dark)'
            },
            {
                'key': 'timezone',
                'value': 'America/New_York',
                'data_type': 'string',
                'description': 'Default timezone for the application'
            }
        ]
        
        print("Adding default configuration...")
        
        for config_data in default_configs:
            # Check if configuration already exists
            existing = db.session.query(Configuration).filter(
                Configuration.key == config_data['key']
            ).first()
            
            if not existing:
                config = Configuration(
                    key=config_data['key'],
                    value=config_data['value'],
                    data_type=config_data['data_type'],
                    description=config_data['description']
                )
                db.session.add(config)
                print(f"  Added: {config_data['key']}")
            else:
                print(f"  Exists: {config_data['key']}")
        
        # Commit all changes
        db.session.commit()
        
        print("Default configuration added successfully!")
        print("\nDatabase initialization complete!")
        
        # Print summary
        print("\nDatabase Summary:")
        print(f"  Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"  Tables created: {len(db.metadata.tables)}")
        print(f"  Configuration entries: {db.session.query(Configuration).count()}")

if __name__ == '__main__':
    initialize_database()
