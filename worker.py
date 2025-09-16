#!/usr/bin/env python3
"""
Background Worker for Charles Schwab Trading Dashboard
Handles alerts, notifications, and background tasks
"""

import os
import sys
import time
import logging
import schedule
from datetime import datetime, timedelta

# Add current directory to Python path
sys.path.append('/app')

# Import our services
try:
    from services.alert_manager import AlertManager
    from services.notification_service import NotificationService
    from services.metrics_calculator import MetricsCalculator
except ImportError as e:
    print(f"Warning: Could not import services: {e}")
    AlertManager = None
    NotificationService = None
    MetricsCalculator = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/worker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TradingWorker:
    def __init__(self):
        try:
            self.alert_manager = AlertManager() if AlertManager else None
            self.notification_service = NotificationService() if NotificationService else None
            self.metrics_calculator = MetricsCalculator() if MetricsCalculator else None
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            self.alert_manager = None
            self.notification_service = None
            self.metrics_calculator = None
        
    def check_alerts(self):
        """Check and process trading alerts"""
        try:
            logger.info("Checking trading alerts...")
            if self.alert_manager:
                # This would integrate with your alert checking logic
                pass
            logger.info("Alert check completed")
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def update_metrics(self):
        """Update portfolio metrics"""
        try:
            logger.info("Updating portfolio metrics...")
            if self.metrics_calculator:
                # This would calculate and store updated metrics
                pass
            logger.info("Metrics update completed")
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
    
    def cleanup_old_data(self):
        """Clean up old data and logs"""
        try:
            logger.info("Cleaning up old data...")
            # This would clean up old logs, expired data, etc.
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def main():
    logger.info("Starting Charles Schwab Trading Dashboard Worker...")
    
    # Create logs directory if it doesn't exist
    os.makedirs('/app/logs', exist_ok=True)
    
    worker = TradingWorker()
    
    # Schedule tasks
    schedule.every(1).minutes.do(worker.check_alerts)
    schedule.every(5).minutes.do(worker.update_metrics)
    schedule.every().day.at("02:00").do(worker.cleanup_old_data)
    
    logger.info("Worker scheduled tasks configured")
    
    # Main worker loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            logger.info("Worker shutdown requested")
            break
        except Exception as e:
            logger.error(f"Worker error: {e}")
            time.sleep(60)  # Wait longer on error

if __name__ == '__main__':
    main()
