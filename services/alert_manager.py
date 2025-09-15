#!/usr/bin/env python3
"""
Alert Manager Service
Manages trading alerts and notifications
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy import and_, or_
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from models.database import db, Alert, Position, Trade, MarketData, NotificationLog
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class AlertManager:
    """
    Service for managing trading alerts and notifications
    """
    
    def __init__(self, db_session=None):
        """
        Initialize the alert manager
        
        Args:
            db_session: Database session (optional)
        """
        self.db_session = db_session or db.session
        self.notification_service = NotificationService()
        self.scheduler = BackgroundScheduler()
        self._setup_scheduler()
    
    def _setup_scheduler(self):
        """Set up the background scheduler for alert checking"""
        try:
            # Check alerts every 30 seconds
            self.scheduler.add_job(
                func=self.check_all_alerts,
                trigger=IntervalTrigger(seconds=30),
                id='alert_checker',
                name='Check all active alerts',
                replace_existing=True
            )
            
            # Start the scheduler
            if not self.scheduler.running:
                self.scheduler.start()
                logger.info("Alert scheduler started")
        except Exception as e:
            logger.error(f"Error setting up alert scheduler: {e}")
    
    def create_alert(self, alert_data: Dict) -> Dict:
        """
        Create a new alert
        
        Args:
            alert_data: Dictionary containing alert configuration
            
        Returns:
            Dictionary containing the created alert or error
        """
        try:
            required_fields = ['name', 'alert_type', 'condition', 'threshold_value']
            for field in required_fields:
                if field not in alert_data:
                    return {'error': f'Missing required field: {field}'}
            
            # Validate alert type
            valid_alert_types = [
                'price', 'pl_loss', 'pl_gain', 'volatility', 'volume', 
                'portfolio_value', 'position_size', 'theta_decay', 'delta_exposure'
            ]
            if alert_data['alert_type'] not in valid_alert_types:
                return {'error': f'Invalid alert type. Must be one of: {valid_alert_types}'}
            
            # Validate condition
            valid_conditions = ['above', 'below', 'equals', 'crosses_above', 'crosses_below']
            if alert_data['condition'] not in valid_conditions:
                return {'error': f'Invalid condition. Must be one of: {valid_conditions}'}
            
            # Create the alert
            alert = Alert(
                name=alert_data['name'],
                alert_type=alert_data['alert_type'],
                symbol=alert_data.get('symbol'),
                condition=alert_data['condition'],
                threshold_value=float(alert_data['threshold_value']),
                email_enabled=alert_data.get('email_enabled', True),
                telegram_enabled=alert_data.get('telegram_enabled', False),
                slack_enabled=alert_data.get('slack_enabled', False),
                message=alert_data.get('message', '')
            )
            
            self.db_session.add(alert)
            self.db_session.commit()
            
            logger.info(f"Created alert: {alert.name} ({alert.alert_type})")
            return {'success': True, 'alert': alert.to_dict()}
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
            self.db_session.rollback()
            return {'error': str(e)}
    
    def update_alert(self, alert_id: int, update_data: Dict) -> Dict:
        """
        Update an existing alert
        
        Args:
            alert_id: ID of the alert to update
            update_data: Dictionary containing fields to update
            
        Returns:
            Dictionary containing the updated alert or error
        """
        try:
            alert = self.db_session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return {'error': 'Alert not found'}
            
            # Update allowed fields
            allowed_fields = [
                'name', 'threshold_value', 'is_active', 'email_enabled',
                'telegram_enabled', 'slack_enabled', 'message'
            ]
            
            for field, value in update_data.items():
                if field in allowed_fields and hasattr(alert, field):
                    setattr(alert, field, value)
            
            self.db_session.commit()
            
            logger.info(f"Updated alert: {alert.name}")
            return {'success': True, 'alert': alert.to_dict()}
            
        except Exception as e:
            logger.error(f"Error updating alert: {e}")
            self.db_session.rollback()
            return {'error': str(e)}
    
    def delete_alert(self, alert_id: int) -> Dict:
        """
        Delete an alert
        
        Args:
            alert_id: ID of the alert to delete
            
        Returns:
            Dictionary containing success status or error
        """
        try:
            alert = self.db_session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return {'error': 'Alert not found'}
            
            alert_name = alert.name
            self.db_session.delete(alert)
            self.db_session.commit()
            
            logger.info(f"Deleted alert: {alert_name}")
            return {'success': True, 'message': f'Alert "{alert_name}" deleted successfully'}
            
        except Exception as e:
            logger.error(f"Error deleting alert: {e}")
            self.db_session.rollback()
            return {'error': str(e)}
    
    def get_alerts(self, active_only: bool = True) -> List[Dict]:
        """
        Get all alerts
        
        Args:
            active_only: Whether to return only active alerts
            
        Returns:
            List of alert dictionaries
        """
        try:
            query = self.db_session.query(Alert)
            if active_only:
                query = query.filter(Alert.is_active == True)
            
            alerts = query.order_by(Alert.created_at.desc()).all()
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return []
    
    def check_all_alerts(self):
        """Check all active alerts and trigger notifications if conditions are met"""
        try:
            active_alerts = self.db_session.query(Alert).filter(
                Alert.is_active == True,
                Alert.is_triggered == False
            ).all()
            
            for alert in active_alerts:
                self._check_single_alert(alert)
                
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
    
    def _check_single_alert(self, alert: Alert):
        """
        Check a single alert and trigger if conditions are met
        
        Args:
            alert: Alert object to check
        """
        try:
            current_value = self._get_current_value(alert)
            if current_value is None:
                return
            
            # Update the current value in the alert
            alert.current_value = current_value
            alert.last_checked = datetime.utcnow()
            
            # Check if alert condition is met
            is_triggered = self._evaluate_alert_condition(alert, current_value)
            
            if is_triggered and not alert.is_triggered:
                self._trigger_alert(alert, current_value)
            
            self.db_session.commit()
            
        except Exception as e:
            logger.error(f"Error checking alert {alert.name}: {e}")
            self.db_session.rollback()
    
    def _get_current_value(self, alert: Alert) -> Optional[float]:
        """
        Get the current value for an alert based on its type
        
        Args:
            alert: Alert object
            
        Returns:
            Current value or None if unable to retrieve
        """
        try:
            if alert.alert_type == 'price' and alert.symbol:
                # Get current price from market data or positions
                position = self.db_session.query(Position).filter(
                    Position.symbol == alert.symbol
                ).first()
                return position.current_price if position else None
            
            elif alert.alert_type == 'pl_loss' or alert.alert_type == 'pl_gain':
                if alert.symbol:
                    # Position-specific P/L
                    position = self.db_session.query(Position).filter(
                        Position.symbol == alert.symbol
                    ).first()
                    return position.unrealized_pl if position else None
                else:
                    # Portfolio-wide P/L
                    total_pl = self.db_session.query(
                        db.func.sum(Position.unrealized_pl)
                    ).scalar()
                    return total_pl or 0
            
            elif alert.alert_type == 'portfolio_value':
                # Total portfolio value
                total_value = self.db_session.query(
                    db.func.sum(Position.market_value)
                ).scalar()
                return total_value or 0
            
            elif alert.alert_type == 'position_size' and alert.symbol:
                # Position size (market value)
                position = self.db_session.query(Position).filter(
                    Position.symbol == alert.symbol
                ).first()
                return abs(position.market_value) if position else None
            
            elif alert.alert_type == 'theta_decay':
                # Total theta decay
                total_theta = self.db_session.query(
                    db.func.sum(Position.theta)
                ).filter(Position.is_option == True).scalar()
                return total_theta or 0
            
            elif alert.alert_type == 'delta_exposure':
                # Total delta exposure
                positions = self.db_session.query(Position).filter(
                    Position.is_option == True
                ).all()
                total_delta_exposure = sum(
                    (pos.delta or 0) * pos.quantity for pos in positions
                )
                return total_delta_exposure
            
            elif alert.alert_type == 'volatility' and alert.symbol:
                # Implied volatility for options
                position = self.db_session.query(Position).filter(
                    Position.symbol == alert.symbol,
                    Position.is_option == True
                ).first()
                return position.implied_volatility if position else None
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current value for alert {alert.name}: {e}")
            return None
    
    def _evaluate_alert_condition(self, alert: Alert, current_value: float) -> bool:
        """
        Evaluate if an alert condition is met
        
        Args:
            alert: Alert object
            current_value: Current value to compare
            
        Returns:
            True if condition is met, False otherwise
        """
        try:
            threshold = alert.threshold_value
            
            if alert.condition == 'above':
                return current_value > threshold
            elif alert.condition == 'below':
                return current_value < threshold
            elif alert.condition == 'equals':
                # Allow for small floating point differences
                return abs(current_value - threshold) < 0.01
            elif alert.condition == 'crosses_above':
                # Would need historical data to implement properly
                return current_value > threshold
            elif alert.condition == 'crosses_below':
                # Would need historical data to implement properly
                return current_value < threshold
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating alert condition: {e}")
            return False
    
    def _trigger_alert(self, alert: Alert, current_value: float):
        """
        Trigger an alert and send notifications
        
        Args:
            alert: Alert object to trigger
            current_value: Current value that triggered the alert
        """
        try:
            # Mark alert as triggered
            alert.is_triggered = True
            alert.triggered_at = datetime.utcnow()
            
            # Create notification message
            message = self._create_alert_message(alert, current_value)
            
            # Send notifications
            notifications_sent = []
            
            if alert.email_enabled:
                result = self.notification_service.send_email_notification(
                    subject=f"Trading Alert: {alert.name}",
                    message=message,
                    alert_id=alert.id
                )
                notifications_sent.append(('email', result))
            
            if alert.telegram_enabled:
                result = self.notification_service.send_telegram_notification(
                    message=message,
                    alert_id=alert.id
                )
                notifications_sent.append(('telegram', result))
            
            if alert.slack_enabled:
                result = self.notification_service.send_slack_notification(
                    message=message,
                    alert_id=alert.id
                )
                notifications_sent.append(('slack', result))
            
            logger.info(f"Alert triggered: {alert.name} - Current value: {current_value}")
            
            # Log notification results
            for notification_type, result in notifications_sent:
                if result.get('success'):
                    logger.info(f"Sent {notification_type} notification for alert: {alert.name}")
                else:
                    logger.error(f"Failed to send {notification_type} notification: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"Error triggering alert {alert.name}: {e}")
    
    def _create_alert_message(self, alert: Alert, current_value: float) -> str:
        """
        Create a notification message for an alert
        
        Args:
            alert: Alert object
            current_value: Current value that triggered the alert
            
        Returns:
            Formatted alert message
        """
        try:
            symbol_text = f" for {alert.symbol}" if alert.symbol else ""
            
            message = f"🚨 TRADING ALERT: {alert.name}\n\n"
            message += f"Alert Type: {alert.alert_type.replace('_', ' ').title()}{symbol_text}\n"
            message += f"Condition: {alert.condition.replace('_', ' ').title()}\n"
            message += f"Threshold: {alert.threshold_value:,.2f}\n"
            message += f"Current Value: {current_value:,.2f}\n"
            message += f"Triggered At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            if alert.message:
                message += f"\nCustom Message: {alert.message}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Error creating alert message: {e}")
            return f"Alert triggered: {alert.name}"
    
    def reset_alert(self, alert_id: int) -> Dict:
        """
        Reset a triggered alert to active state
        
        Args:
            alert_id: ID of the alert to reset
            
        Returns:
            Dictionary containing success status or error
        """
        try:
            alert = self.db_session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return {'error': 'Alert not found'}
            
            alert.is_triggered = False
            alert.triggered_at = None
            self.db_session.commit()
            
            logger.info(f"Reset alert: {alert.name}")
            return {'success': True, 'message': f'Alert "{alert.name}" reset successfully'}
            
        except Exception as e:
            logger.error(f"Error resetting alert: {e}")
            self.db_session.rollback()
            return {'error': str(e)}
    
    def get_alert_history(self, days: int = 7) -> List[Dict]:
        """
        Get alert history for the specified number of days
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of triggered alerts
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            alerts = self.db_session.query(Alert).filter(
                Alert.triggered_at >= start_date
            ).order_by(Alert.triggered_at.desc()).all()
            
            return [alert.to_dict() for alert in alerts]
            
        except Exception as e:
            logger.error(f"Error getting alert history: {e}")
            return []
    
    def get_notification_logs(self, alert_id: int = None, days: int = 7) -> List[Dict]:
        """
        Get notification logs
        
        Args:
            alert_id: Optional alert ID to filter by
            days: Number of days to look back
            
        Returns:
            List of notification logs
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db_session.query(NotificationLog).filter(
                NotificationLog.sent_at >= start_date
            )
            
            if alert_id:
                query = query.filter(NotificationLog.alert_id == alert_id)
            
            logs = query.order_by(NotificationLog.sent_at.desc()).all()
            return [log.to_dict() for log in logs]
            
        except Exception as e:
            logger.error(f"Error getting notification logs: {e}")
            return []
    
    def test_alert(self, alert_id: int) -> Dict:
        """
        Test an alert by sending a test notification
        
        Args:
            alert_id: ID of the alert to test
            
        Returns:
            Dictionary containing test results
        """
        try:
            alert = self.db_session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return {'error': 'Alert not found'}
            
            # Create test message
            test_message = f"🧪 TEST ALERT: {alert.name}\n\n"
            test_message += f"This is a test notification for your alert.\n"
            test_message += f"Alert Type: {alert.alert_type.replace('_', ' ').title()}\n"
            test_message += f"Threshold: {alert.threshold_value:,.2f}\n"
            test_message += f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            results = {}
            
            if alert.email_enabled:
                result = self.notification_service.send_email_notification(
                    subject=f"Test Alert: {alert.name}",
                    message=test_message,
                    alert_id=alert.id
                )
                results['email'] = result
            
            if alert.telegram_enabled:
                result = self.notification_service.send_telegram_notification(
                    message=test_message,
                    alert_id=alert.id
                )
                results['telegram'] = result
            
            if alert.slack_enabled:
                result = self.notification_service.send_slack_notification(
                    message=test_message,
                    alert_id=alert.id
                )
                results['slack'] = result
            
            return {'success': True, 'results': results}
            
        except Exception as e:
            logger.error(f"Error testing alert: {e}")
            return {'error': str(e)}
    
    def shutdown(self):
        """Shutdown the alert manager and scheduler"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Alert scheduler shutdown")
        except Exception as e:
            logger.error(f"Error shutting down alert manager: {e}")
