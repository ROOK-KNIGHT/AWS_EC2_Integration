#!/usr/bin/env python3
"""
Notification Service
Handles email, Telegram, and Slack notifications
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List
from datetime import datetime, timedelta

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False

from models.database import db, NotificationLog

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Service for sending notifications via email, Telegram, and Slack
    """
    
    def __init__(self):
        """Initialize the notification service"""
        # Email configuration
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.email_from = os.getenv('EMAIL_FROM', self.email_user)
        self.email_to = os.getenv('EMAIL_TO', self.email_user)
        
        # Telegram configuration
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.telegram_bot = None
        
        if TELEGRAM_AVAILABLE and self.telegram_token:
            try:
                self.telegram_bot = Bot(token=self.telegram_token)
            except Exception as e:
                logger.error(f"Error initializing Telegram bot: {e}")
        
        # Slack configuration
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.slack_channel = os.getenv('SLACK_CHANNEL', '#trading-alerts')
        self.slack_client = None
        
        if SLACK_AVAILABLE and self.slack_token:
            try:
                self.slack_client = WebClient(token=self.slack_token)
            except Exception as e:
                logger.error(f"Error initializing Slack client: {e}")
    
    def send_email_notification(self, subject: str, message: str, 
                              recipient: str = None, alert_id: int = None) -> Dict:
        """
        Send email notification
        
        Args:
            subject: Email subject
            message: Email message
            recipient: Email recipient (optional, uses default if not provided)
            alert_id: Associated alert ID (optional)
            
        Returns:
            Dictionary containing success status and details
        """
        if not self.email_user or not self.email_password:
            error_msg = "Email credentials not configured"
            self._log_notification('email', recipient or self.email_to, subject, 
                                 message, 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
        
        recipient = recipient or self.email_to
        if not recipient:
            error_msg = "No email recipient specified"
            self._log_notification('email', 'unknown', subject, message, 
                                 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Add body to email
            msg.attach(MIMEText(message, 'plain'))
            
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable security
            server.login(self.email_user, self.email_password)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.email_from, recipient, text)
            server.quit()
            
            logger.info(f"Email sent successfully to {recipient}")
            self._log_notification('email', recipient, subject, message, 
                                 'sent', None, alert_id)
            
            return {'success': True, 'recipient': recipient}
            
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(error_msg)
            self._log_notification('email', recipient, subject, message, 
                                 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
    
    def send_telegram_notification(self, message: str, chat_id: str = None, 
                                 alert_id: int = None) -> Dict:
        """
        Send Telegram notification
        
        Args:
            message: Message to send
            chat_id: Telegram chat ID (optional, uses default if not provided)
            alert_id: Associated alert ID (optional)
            
        Returns:
            Dictionary containing success status and details
        """
        if not TELEGRAM_AVAILABLE:
            error_msg = "Telegram library not available. Install python-telegram-bot"
            self._log_notification('telegram', chat_id or 'unknown', 'N/A', 
                                 message, 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
        
        if not self.telegram_bot or not self.telegram_token:
            error_msg = "Telegram bot not configured"
            self._log_notification('telegram', chat_id or 'unknown', 'N/A', 
                                 message, 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
        
        chat_id = chat_id or self.telegram_chat_id
        if not chat_id:
            error_msg = "No Telegram chat ID specified"
            self._log_notification('telegram', 'unknown', 'N/A', message, 
                                 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
        
        try:
            # Send message
            self.telegram_bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"Telegram message sent successfully to {chat_id}")
            self._log_notification('telegram', chat_id, 'N/A', message, 
                                 'sent', None, alert_id)
            
            return {'success': True, 'chat_id': chat_id}
            
        except TelegramError as e:
            error_msg = f"Telegram error: {str(e)}"
            logger.error(error_msg)
            self._log_notification('telegram', chat_id, 'N/A', message, 
                                 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Failed to send Telegram message: {str(e)}"
            logger.error(error_msg)
            self._log_notification('telegram', chat_id, 'N/A', message, 
                                 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
    
    def send_slack_notification(self, message: str, channel: str = None, 
                              alert_id: int = None) -> Dict:
        """
        Send Slack notification
        
        Args:
            message: Message to send
            channel: Slack channel (optional, uses default if not provided)
            alert_id: Associated alert ID (optional)
            
        Returns:
            Dictionary containing success status and details
        """
        if not SLACK_AVAILABLE:
            error_msg = "Slack library not available. Install slack-sdk"
            self._log_notification('slack', channel or 'unknown', 'N/A', 
                                 message, 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
        
        if not self.slack_client or not self.slack_token:
            error_msg = "Slack client not configured"
            self._log_notification('slack', channel or 'unknown', 'N/A', 
                                 message, 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
        
        channel = channel or self.slack_channel
        if not channel:
            error_msg = "No Slack channel specified"
            self._log_notification('slack', 'unknown', 'N/A', message, 
                                 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
        
        try:
            # Send message
            response = self.slack_client.chat_postMessage(
                channel=channel,
                text=message
            )
            
            if response['ok']:
                logger.info(f"Slack message sent successfully to {channel}")
                self._log_notification('slack', channel, 'N/A', message, 
                                     'sent', None, alert_id)
                return {'success': True, 'channel': channel}
            else:
                error_msg = f"Slack API error: {response.get('error', 'Unknown error')}"
                logger.error(error_msg)
                self._log_notification('slack', channel, 'N/A', message, 
                                     'failed', error_msg, alert_id)
                return {'success': False, 'error': error_msg}
            
        except SlackApiError as e:
            error_msg = f"Slack API error: {str(e)}"
            logger.error(error_msg)
            self._log_notification('slack', channel, 'N/A', message, 
                                 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f"Failed to send Slack message: {str(e)}"
            logger.error(error_msg)
            self._log_notification('slack', channel, 'N/A', message, 
                                 'failed', error_msg, alert_id)
            return {'success': False, 'error': error_msg}
    
    def send_multi_channel_notification(self, subject: str, message: str, 
                                      channels: Dict[str, bool] = None, 
                                      alert_id: int = None) -> Dict:
        """
        Send notification to multiple channels
        
        Args:
            subject: Notification subject
            message: Notification message
            channels: Dictionary specifying which channels to use
                     {'email': True, 'telegram': False, 'slack': True}
            alert_id: Associated alert ID (optional)
            
        Returns:
            Dictionary containing results for each channel
        """
        if channels is None:
            channels = {'email': True, 'telegram': False, 'slack': False}
        
        results = {}
        
        if channels.get('email', False):
            results['email'] = self.send_email_notification(
                subject=subject, 
                message=message, 
                alert_id=alert_id
            )
        
        if channels.get('telegram', False):
            results['telegram'] = self.send_telegram_notification(
                message=f"{subject}\n\n{message}", 
                alert_id=alert_id
            )
        
        if channels.get('slack', False):
            results['slack'] = self.send_slack_notification(
                message=f"*{subject}*\n{message}", 
                alert_id=alert_id
            )
        
        # Summary
        successful_channels = [channel for channel, result in results.items() 
                             if result.get('success', False)]
        failed_channels = [channel for channel, result in results.items() 
                         if not result.get('success', False)]
        
        return {
            'success': len(successful_channels) > 0,
            'successful_channels': successful_channels,
            'failed_channels': failed_channels,
            'results': results
        }
    
    def test_notifications(self) -> Dict:
        """
        Test all configured notification channels
        
        Returns:
            Dictionary containing test results for each channel
        """
        test_subject = "Trading Dashboard Test Notification"
        test_message = f"This is a test notification from your trading dashboard.\n\nSent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        results = {}
        
        # Test email
        if self.email_user and self.email_password:
            results['email'] = self.send_email_notification(
                subject=test_subject,
                message=test_message
            )
        else:
            results['email'] = {'success': False, 'error': 'Email not configured'}
        
        # Test Telegram
        if self.telegram_bot and self.telegram_chat_id:
            results['telegram'] = self.send_telegram_notification(
                message=f"{test_subject}\n\n{test_message}"
            )
        else:
            results['telegram'] = {'success': False, 'error': 'Telegram not configured'}
        
        # Test Slack
        if self.slack_client and self.slack_channel:
            results['slack'] = self.send_slack_notification(
                message=f"*{test_subject}*\n{test_message}"
            )
        else:
            results['slack'] = {'success': False, 'error': 'Slack not configured'}
        
        return results
    
    def get_notification_status(self) -> Dict:
        """
        Get the status of all notification channels
        
        Returns:
            Dictionary containing configuration status for each channel
        """
        return {
            'email': {
                'configured': bool(self.email_user and self.email_password),
                'smtp_server': self.smtp_server,
                'smtp_port': self.smtp_port,
                'from_address': self.email_from,
                'to_address': self.email_to
            },
            'telegram': {
                'configured': bool(self.telegram_bot and self.telegram_chat_id),
                'available': TELEGRAM_AVAILABLE,
                'chat_id': self.telegram_chat_id
            },
            'slack': {
                'configured': bool(self.slack_client and self.slack_channel),
                'available': SLACK_AVAILABLE,
                'channel': self.slack_channel
            }
        }
    
    def _log_notification(self, notification_type: str, recipient: str, 
                         subject: str, message: str, status: str, 
                         error_message: str = None, alert_id: int = None):
        """
        Log notification attempt to database
        
        Args:
            notification_type: Type of notification (email, telegram, slack)
            recipient: Notification recipient
            subject: Notification subject
            message: Notification message
            status: Status (sent, failed, pending)
            error_message: Error message if failed
            alert_id: Associated alert ID
        """
        try:
            log_entry = NotificationLog(
                alert_id=alert_id,
                notification_type=notification_type,
                recipient=recipient,
                subject=subject,
                message=message,
                status=status,
                error_message=error_message
            )
            
            db.session.add(log_entry)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error logging notification: {e}")
            # Don't let logging errors affect the main notification flow
            try:
                db.session.rollback()
            except:
                pass
    
    def get_notification_history(self, days: int = 7, 
                               notification_type: str = None) -> List[Dict]:
        """
        Get notification history
        
        Args:
            days: Number of days to look back
            notification_type: Filter by notification type (optional)
            
        Returns:
            List of notification log entries
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            query = db.session.query(NotificationLog).filter(
                NotificationLog.sent_at >= start_date
            )
            
            if notification_type:
                query = query.filter(NotificationLog.notification_type == notification_type)
            
            logs = query.order_by(NotificationLog.sent_at.desc()).all()
            return [log.to_dict() for log in logs]
            
        except Exception as e:
            logger.error(f"Error getting notification history: {e}")
            return []
    
    def cleanup_old_logs(self, days: int = 30):
        """
        Clean up old notification logs
        
        Args:
            days: Number of days to keep logs
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            deleted_count = db.session.query(NotificationLog).filter(
                NotificationLog.sent_at < cutoff_date
            ).delete()
            
            db.session.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old notification logs")
            
        except Exception as e:
            logger.error(f"Error cleaning up notification logs: {e}")
            db.session.rollback()
