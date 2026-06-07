"""
WhatsApp Integration Service for Trading Notifications

This service provides WhatsApp notification capabilities using:
1. Twilio WhatsApp API (recommended for production)
2. WhatsApp Business API
3. Meta Cloud API for WhatsApp

Features:
- Order notifications
- Trade alerts (entry, exit, stop-loss hits)
- Daily summary reports
- Custom alerts

Configuration:
Set the following environment variables:
- WHATSAPP_PROVIDER: 'twilio', 'meta', or 'business_api'
- WHATSAPP_ACCOUNT_SID: Twilio account SID (for Twilio)
- WHATSAPP_AUTH_TOKEN: Twilio auth token (for Twilio)
- WHATSAPP_FROM_NUMBER: WhatsApp sender number
- WHATSAPP_ACCESS_TOKEN: Meta/Business API access token
- WHATSAPP_PHONE_NUMBER_ID: Meta API phone number ID
"""

import os
import json
import logging
import requests
from typing import Dict, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Thread pool for async notifications
whatsapp_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="whatsapp_notify")


class WhatsAppProvider:
    """Base class for WhatsApp providers"""
    
    def send_message(self, to_number: str, message: str) -> bool:
        raise NotImplementedError
    
    def send_template(self, to_number: str, template_name: str, parameters: Dict) -> bool:
        raise NotImplementedError


class TwilioWhatsAppProvider(WhatsAppProvider):
    """WhatsApp provider using Twilio API"""
    
    def __init__(self):
        self.account_sid = os.getenv('WHATSAPP_ACCOUNT_SID', os.getenv('TWILIO_ACCOUNT_SID'))
        self.auth_token = os.getenv('WHATSAPP_AUTH_TOKEN', os.getenv('TWILIO_AUTH_TOKEN'))
        self.from_number = os.getenv('WHATSAPP_FROM_NUMBER', 'whatsapp:+14155238886')  # Twilio sandbox
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        
        self.is_configured = bool(self.account_sid and self.auth_token)
    
    def send_message(self, to_number: str, message: str) -> bool:
        """Send WhatsApp message via Twilio"""
        if not self.is_configured:
            logger.warning("Twilio WhatsApp not configured")
            return False
        
        try:
            # Format number for WhatsApp
            if not to_number.startswith('whatsapp:'):
                to_number = f"whatsapp:{to_number}"
            
            data = {
                'From': self.from_number,
                'To': to_number,
                'Body': message
            }
            
            response = requests.post(
                self.base_url,
                data=data,
                auth=(self.account_sid, self.auth_token),
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"WhatsApp message sent via Twilio to {to_number}")
                return True
            else:
                logger.error(f"Twilio WhatsApp error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Twilio WhatsApp message: {e}")
            return False
    
    def send_template(self, to_number: str, template_name: str, parameters: Dict) -> bool:
        """Send template message via Twilio"""
        # Twilio uses content templates differently
        # For now, format as regular message
        message = self._format_template(template_name, parameters)
        return self.send_message(to_number, message)
    
    def _format_template(self, template_name: str, parameters: Dict) -> str:
        """Format template message"""
        templates = {
            'trade_alert': "🔔 *Trade Alert*\n\nMetal: {metal}\nAction: {action}\nPrice: {price}\nTime: {time}",
            'stop_loss_hit': "⚠️ *Stop Loss Hit*\n\nMetal: {metal}\nEntry: {entry_price}\nExit: {exit_price}\nLoss: {loss}",
            'take_profit': "✅ *Take Profit Reached*\n\nMetal: {metal}\nEntry: {entry_price}\nExit: {exit_price}\nProfit: {profit}",
            'daily_summary': "📊 *Daily Summary*\n\nDate: {date}\nTrades: {total_trades}\nP&L: {pnl}\nWin Rate: {win_rate}%"
        }
        
        template = templates.get(template_name, template_name)
        return template.format(**parameters)


class MetaWhatsAppProvider(WhatsAppProvider):
    """WhatsApp provider using Meta (Facebook) Cloud API"""
    
    def __init__(self):
        self.access_token = os.getenv('WHATSAPP_ACCESS_TOKEN')
        self.phone_number_id = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
        self.base_url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}/messages"
        
        self.is_configured = bool(self.access_token and self.phone_number_id)
    
    def send_message(self, to_number: str, message: str) -> bool:
        """Send WhatsApp message via Meta Cloud API"""
        if not self.is_configured:
            logger.warning("Meta WhatsApp API not configured")
            return False
        
        try:
            # Remove 'whatsapp:' prefix if present
            if to_number.startswith('whatsapp:'):
                to_number = to_number.replace('whatsapp:', '')
            
            # Remove + and any spaces
            to_number = to_number.replace('+', '').replace(' ', '')
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'messaging_product': 'whatsapp',
                'recipient_type': 'individual',
                'to': to_number,
                'type': 'text',
                'text': {
                    'preview_url': False,
                    'body': message
                }
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"WhatsApp message sent via Meta API to {to_number}")
                return True
            else:
                logger.error(f"Meta WhatsApp API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Meta WhatsApp message: {e}")
            return False
    
    def send_template(self, to_number: str, template_name: str, parameters: Dict) -> bool:
        """Send template message via Meta Cloud API"""
        if not self.is_configured:
            return False
        
        try:
            if to_number.startswith('whatsapp:'):
                to_number = to_number.replace('whatsapp:', '')
            to_number = to_number.replace('+', '').replace(' ', '')
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Format components for Meta template API
            components = []
            if parameters:
                body_params = [{'type': 'text', 'text': str(v)} for v in parameters.values()]
                components.append({
                    'type': 'body',
                    'parameters': body_params
                })
            
            data = {
                'messaging_product': 'whatsapp',
                'recipient_type': 'individual',
                'to': to_number,
                'type': 'template',
                'template': {
                    'name': template_name,
                    'language': {'code': 'en'},
                    'components': components
                }
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"WhatsApp template sent via Meta API to {to_number}")
                return True
            else:
                logger.error(f"Meta WhatsApp template error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Meta WhatsApp template: {e}")
            return False


class WhatsAppService:
    """Main WhatsApp service for trading notifications"""
    
    def __init__(self):
        self.provider = self._initialize_provider()
        self.enabled = self.provider is not None
        
        # Notification templates
        self.templates = {
            'order_placed': "📈 *Order Placed*\n\n{details}",
            'trade_entry': "🔔 *{metal} {action} Entry*\n\nPrice: ₹{price:,.2f}\nQuantity: {quantity}\nStop Loss: ₹{stop_loss:,.2f}\nTake Profit: ₹{take_profit:,.2f}\nTime: {time}",
            'trade_exit': "{emoji} *{metal} Exit - {reason}*\n\nEntry: ₹{entry_price:,.2f}\nExit: ₹{exit_price:,.2f}\nP&L: ₹{pnl:,.2f} ({pnl_pct:.2f}%)\nTime: {time}",
            'stop_loss_hit': "⚠️ *Stop Loss Hit - {metal}*\n\nEntry: ₹{entry_price:,.2f}\nStop Loss: ₹{stop_loss:,.2f}\nLoss: ₹{loss:,.2f} ({loss_pct:.2f}%)\nTime: {time}",
            'take_profit_hit': "✅ *Take Profit Reached - {metal}*\n\nEntry: ₹{entry_price:,.2f}\nTarget: ₹{take_profit:,.2f}\nProfit: ₹{profit:,.2f} ({profit_pct:.2f}%)\nTime: {time}",
            'stop_loss_updated': "🔄 *Stop Loss Updated - {metal}*\n\nOld SL: ₹{old_sl:,.2f}\nNew SL: ₹{new_sl:,.2f}\nCurrent Price: ₹{current_price:,.2f}\nTime: {time}",
            'daily_summary': "📊 *Daily Trading Summary*\n\nDate: {date}\n\n*Performance:*\nTotal Trades: {total_trades}\nWinning: {winning_trades}\nLosing: {losing_trades}\nWin Rate: {win_rate:.1f}%\n\n*P&L:*\nGross P&L: ₹{gross_pnl:,.2f}\nNet P&L: ₹{net_pnl:,.2f}\n\n*Risk:*\nMax Drawdown: {max_drawdown:.2f}%",
            'signal_alert': "🎯 *Trading Signal - {metal}*\n\nSignal: {signal}\nStrength: {strength:.1f}%\nCurrent Price: ₹{price:,.2f}\n\n*Indicators:*\n{indicators}\n\nTime: {time}",
            'error_alert': "🚨 *Error Alert*\n\n{error_message}\n\nTime: {time}"
        }
    
    def _initialize_provider(self) -> Optional[WhatsAppProvider]:
        """Initialize the appropriate WhatsApp provider"""
        provider_type = os.getenv('WHATSAPP_PROVIDER', 'twilio').lower()
        
        if provider_type == 'twilio':
            provider = TwilioWhatsAppProvider()
            if provider.is_configured:
                logger.info("WhatsApp provider: Twilio")
                return provider
        
        elif provider_type == 'meta':
            provider = MetaWhatsAppProvider()
            if provider.is_configured:
                logger.info("WhatsApp provider: Meta Cloud API")
                return provider
        
        # Try both if specific one not configured
        for ProviderClass in [TwilioWhatsAppProvider, MetaWhatsAppProvider]:
            provider = ProviderClass()
            if provider.is_configured:
                logger.info(f"WhatsApp provider: {ProviderClass.__name__}")
                return provider
        
        logger.warning("No WhatsApp provider configured")
        return None
    
    def is_available(self) -> bool:
        """Check if WhatsApp service is available"""
        return self.enabled
    
    def send_notification(self, to_number: str, message: str) -> bool:
        """Send a notification message"""
        if not self.enabled:
            logger.warning("WhatsApp service not enabled")
            return False
        
        return self.provider.send_message(to_number, message)
    
    def send_notification_async(self, to_number: str, message: str):
        """Send notification asynchronously (non-blocking)"""
        if not self.enabled:
            return
        
        whatsapp_executor.submit(self.send_notification, to_number, message)
    
    def send_trade_entry_alert(self, to_number: str, metal: str, action: str, price: float, 
                               quantity: int, stop_loss: float, take_profit: float) -> bool:
        """Send trade entry notification"""
        message = self.templates['trade_entry'].format(
            metal=metal,
            action=action,
            price=price,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit,
            time=datetime.now().strftime('%H:%M:%S')
        )
        return self.send_notification(to_number, message)
    
    def send_trade_exit_alert(self, to_number: str, metal: str, reason: str,
                              entry_price: float, exit_price: float, pnl: float, pnl_pct: float) -> bool:
        """Send trade exit notification"""
        emoji = "✅" if pnl > 0 else "❌"
        message = self.templates['trade_exit'].format(
            emoji=emoji,
            metal=metal,
            reason=reason,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            pnl_pct=pnl_pct,
            time=datetime.now().strftime('%H:%M:%S')
        )
        return self.send_notification(to_number, message)
    
    def send_stop_loss_alert(self, to_number: str, metal: str, entry_price: float,
                             stop_loss: float, loss: float, loss_pct: float) -> bool:
        """Send stop loss hit notification"""
        message = self.templates['stop_loss_hit'].format(
            metal=metal,
            entry_price=entry_price,
            stop_loss=stop_loss,
            loss=loss,
            loss_pct=loss_pct,
            time=datetime.now().strftime('%H:%M:%S')
        )
        return self.send_notification(to_number, message)
    
    def send_take_profit_alert(self, to_number: str, metal: str, entry_price: float,
                               take_profit: float, profit: float, profit_pct: float) -> bool:
        """Send take profit notification"""
        message = self.templates['take_profit_hit'].format(
            metal=metal,
            entry_price=entry_price,
            take_profit=take_profit,
            profit=profit,
            profit_pct=profit_pct,
            time=datetime.now().strftime('%H:%M:%S')
        )
        return self.send_notification(to_number, message)
    
    def send_stop_loss_update_alert(self, to_number: str, metal: str, old_sl: float,
                                    new_sl: float, current_price: float) -> bool:
        """Send stop loss update notification"""
        message = self.templates['stop_loss_updated'].format(
            metal=metal,
            old_sl=old_sl,
            new_sl=new_sl,
            current_price=current_price,
            time=datetime.now().strftime('%H:%M:%S')
        )
        return self.send_notification(to_number, message)
    
    def send_daily_summary(self, to_number: str, date: str, total_trades: int,
                           winning_trades: int, losing_trades: int, win_rate: float,
                           gross_pnl: float, net_pnl: float, max_drawdown: float) -> bool:
        """Send daily trading summary"""
        message = self.templates['daily_summary'].format(
            date=date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            gross_pnl=gross_pnl,
            net_pnl=net_pnl,
            max_drawdown=max_drawdown
        )
        return self.send_notification(to_number, message)
    
    def send_signal_alert(self, to_number: str, metal: str, signal: str,
                          strength: float, price: float, indicators: str) -> bool:
        """Send trading signal alert"""
        message = self.templates['signal_alert'].format(
            metal=metal,
            signal=signal,
            strength=strength,
            price=price,
            indicators=indicators,
            time=datetime.now().strftime('%H:%M:%S')
        )
        return self.send_notification(to_number, message)
    
    def send_error_alert(self, to_number: str, error_message: str) -> bool:
        """Send error alert"""
        message = self.templates['error_alert'].format(
            error_message=error_message,
            time=datetime.now().strftime('%H:%M:%S')
        )
        return self.send_notification(to_number, message)
    
    def send_broadcast(self, numbers: List[str], message: str) -> Dict[str, bool]:
        """Send message to multiple numbers"""
        results = {}
        for number in numbers:
            results[number] = self.send_notification(number, message)
        return results


# Global instance
whatsapp_service = WhatsAppService()
