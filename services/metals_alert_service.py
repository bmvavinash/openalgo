"""
Metals Alert Service

Unified notification service for metals trading that supports:
1. Telegram notifications
2. WhatsApp notifications
3. Both simultaneously

Features:
- Trade entry/exit alerts
- Stop loss updates
- Daily summaries
- Custom alerts
- User preferences for notification channels
"""

import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Thread pool for async notifications
metals_alert_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="metals_alert")


class MetalsAlertService:
    """
    Unified alert service for metals trading
    
    Supports both Telegram and WhatsApp notifications based on user preferences.
    """
    
    def __init__(self):
        self.telegram_service = None
        self.whatsapp_service = None
        self._load_services()
        
        # Alert templates
        self.templates = {
            'trade_entry': {
                'title': '{emoji} {metal} {action} Entry',
                'body': (
                    "Price: ₹{price:,.2f}\n"
                    "Quantity: {quantity}\n"
                    "Stop Loss: ₹{stop_loss:,.2f} ({sl_pct:.2f}%)\n"
                    "Take Profit: ₹{take_profit:,.2f} ({tp_pct:.2f}%)\n"
                    "Signal Strength: {signal_strength:.1f}%\n"
                    "Volatility: {volatility_regime}\n"
                    "Time: {time}"
                )
            },
            'trade_exit': {
                'title': '{emoji} {metal} Exit - {reason}',
                'body': (
                    "Entry: ₹{entry_price:,.2f}\n"
                    "Exit: ₹{exit_price:,.2f}\n"
                    "P&L: ₹{pnl:,.2f} ({pnl_pct:.2f}%)\n"
                    "Holding Time: {holding_time}\n"
                    "Daily P&L: ₹{daily_pnl:,.2f}\n"
                    "Time: {time}"
                )
            },
            'stop_loss_updated': {
                'title': '🔄 {metal} Stop Loss Updated',
                'body': (
                    "Old SL: ₹{old_sl:,.2f}\n"
                    "New SL: ₹{new_sl:,.2f}\n"
                    "Current Price: ₹{current_price:,.2f}\n"
                    "P&L if hit: {potential_pnl_pct:.2f}%\n"
                    "Reason: {reason}\n"
                    "Time: {time}"
                )
            },
            'daily_summary': {
                'title': '📊 Metals Daily Summary - {date}',
                'body': (
                    "*Gold Performance:*\n"
                    "Trades: {gold_trades} | Win Rate: {gold_win_rate:.1f}%\n"
                    "P&L: ₹{gold_pnl:,.2f}\n\n"
                    "*Silver Performance:*\n"
                    "Trades: {silver_trades} | Win Rate: {silver_win_rate:.1f}%\n"
                    "P&L: ₹{silver_pnl:,.2f}\n\n"
                    "*Total:*\n"
                    "Net P&L: ₹{total_pnl:,.2f}\n"
                    "Max Drawdown: {max_drawdown:.2f}%"
                )
            },
            'signal_alert': {
                'title': '🎯 {metal} Signal - {signal}',
                'body': (
                    "Strength: {strength:.1f}%\n"
                    "Price: ₹{price:,.2f}\n"
                    "Trend: {trend}\n\n"
                    "*Indicators:*\n"
                    "EMA: {ema_signal}\n"
                    "RSI: {rsi_value:.1f} ({rsi_signal})\n"
                    "MACD: {macd_signal}\n"
                    "Volume: {volume_signal}\n\n"
                    "Time: {time}"
                )
            },
            'error_alert': {
                'title': '🚨 Metals Strategy Error',
                'body': (
                    "Strategy: {strategy}\n"
                    "Metal: {metal}\n"
                    "Error: {error_message}\n"
                    "Time: {time}"
                )
            },
            'strategy_started': {
                'title': '▶️ {metal} Strategy Started',
                'body': (
                    "Strategy: {strategy_name}\n"
                    "Symbol: {symbol}\n"
                    "Exchange: {exchange}\n"
                    "Stop Loss Type: {stop_loss_type}\n"
                    "Time: {time}"
                )
            },
            'strategy_stopped': {
                'title': '⏹️ {metal} Strategy Stopped',
                'body': (
                    "Strategy: {strategy_name}\n"
                    "Reason: {reason}\n"
                    "Time: {time}"
                )
            }
        }
    
    def _load_services(self):
        """Load notification services"""
        # Load Telegram service
        try:
            from services.telegram_alert_service import telegram_alert_service
            self.telegram_service = telegram_alert_service
            logger.info("Telegram alert service loaded")
        except ImportError as e:
            logger.warning(f"Telegram alert service not available: {e}")
        
        # Load WhatsApp service
        try:
            from services.whatsapp_service import whatsapp_service
            self.whatsapp_service = whatsapp_service
            logger.info("WhatsApp service loaded")
        except ImportError as e:
            logger.warning(f"WhatsApp service not available: {e}")
    
    def _get_user_preferences(self, api_key: str) -> Dict:
        """Get user notification preferences from database"""
        try:
            from database.metals_db import get_user_metals_strategies
            from database.auth_db import get_username_by_apikey
            
            username = get_username_by_apikey(api_key)
            if not username:
                return {'telegram': True, 'whatsapp': False}
            
            # Get user's strategy preferences
            strategies = get_user_metals_strategies(username)
            if strategies:
                # Use first strategy's preferences as default
                return {
                    'telegram': strategies[0].telegram_alerts,
                    'whatsapp': strategies[0].whatsapp_alerts
                }
            
            return {'telegram': True, 'whatsapp': False}
            
        except Exception as e:
            logger.warning(f"Could not get user preferences: {e}")
            return {'telegram': True, 'whatsapp': False}
    
    def _get_user_whatsapp_number(self, api_key: str) -> Optional[str]:
        """Get user's WhatsApp number"""
        try:
            # Try to get from database
            from database.auth_db import get_username_by_apikey
            
            # For now, use environment variable as fallback
            # In production, this would be fetched from user profile
            return os.getenv('DEFAULT_WHATSAPP_NUMBER')
            
        except Exception:
            return None
    
    def _format_message(self, template_name: str, **kwargs) -> str:
        """Format message from template"""
        template = self.templates.get(template_name, {})
        title = template.get('title', '')
        body = template.get('body', '')
        
        try:
            formatted_title = title.format(**kwargs)
            formatted_body = body.format(**kwargs)
            return f"{formatted_title}\n\n{formatted_body}"
        except KeyError as e:
            logger.warning(f"Missing template parameter: {e}")
            return f"{template_name}: {str(kwargs)}"
    
    def send_metals_alert(self, metal_type: str, message: str, api_key: str = None,
                          send_telegram: bool = None, send_whatsapp: bool = None):
        """
        Send alert to configured channels
        
        Args:
            metal_type: GOLD, SILVER, etc.
            message: Alert message
            api_key: User's API key for looking up preferences
            send_telegram: Override for Telegram (None = use preference)
            send_whatsapp: Override for WhatsApp (None = use preference)
        """
        try:
            # Get user preferences
            prefs = self._get_user_preferences(api_key) if api_key else {'telegram': True, 'whatsapp': False}
            
            # Apply overrides
            use_telegram = send_telegram if send_telegram is not None else prefs.get('telegram', True)
            use_whatsapp = send_whatsapp if send_whatsapp is not None else prefs.get('whatsapp', False)
            
            # Send via Telegram
            if use_telegram and self.telegram_service:
                metals_alert_executor.submit(
                    self._send_telegram_alert,
                    message, api_key
                )
            
            # Send via WhatsApp
            if use_whatsapp and self.whatsapp_service and self.whatsapp_service.is_available():
                whatsapp_number = self._get_user_whatsapp_number(api_key)
                if whatsapp_number:
                    metals_alert_executor.submit(
                        self._send_whatsapp_alert,
                        whatsapp_number, message
                    )
            
        except Exception as e:
            logger.error(f"Error sending metals alert: {e}")
    
    def _send_telegram_alert(self, message: str, api_key: str):
        """Send alert via Telegram"""
        try:
            if self.telegram_service:
                # Use the telegram alert service's existing infrastructure
                self.telegram_service.send_order_alert(
                    order_type='metals',
                    order_data={'message': message},
                    response={'status': 'success', 'mode': 'live'},
                    api_key=api_key
                )
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
    
    def _send_whatsapp_alert(self, number: str, message: str):
        """Send alert via WhatsApp"""
        try:
            if self.whatsapp_service:
                self.whatsapp_service.send_notification(number, message)
        except Exception as e:
            logger.error(f"Error sending WhatsApp alert: {e}")
    
    # Specific alert methods
    
    def send_trade_entry_alert(self, metal_type: str, action: str, price: float,
                               quantity: int, stop_loss: float, take_profit: float,
                               signal_strength: float, volatility_regime: str,
                               api_key: str = None):
        """Send trade entry alert"""
        emoji = "🥇" if metal_type == "GOLD" else "🪙"
        sl_pct = abs((price - stop_loss) / price * 100)
        tp_pct = abs((take_profit - price) / price * 100)
        
        message = self._format_message(
            'trade_entry',
            emoji=emoji,
            metal=metal_type,
            action=action,
            price=price,
            quantity=quantity,
            stop_loss=stop_loss,
            sl_pct=sl_pct,
            take_profit=take_profit,
            tp_pct=tp_pct,
            signal_strength=signal_strength,
            volatility_regime=volatility_regime,
            time=datetime.now().strftime('%H:%M:%S')
        )
        
        self.send_metals_alert(metal_type, message, api_key)
    
    def send_trade_exit_alert(self, metal_type: str, reason: str, entry_price: float,
                              exit_price: float, pnl: float, pnl_pct: float,
                              holding_time: str, daily_pnl: float, api_key: str = None):
        """Send trade exit alert"""
        emoji = "✅" if pnl > 0 else "❌"
        
        message = self._format_message(
            'trade_exit',
            emoji=emoji,
            metal=metal_type,
            reason=reason,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            pnl_pct=pnl_pct,
            holding_time=holding_time,
            daily_pnl=daily_pnl,
            time=datetime.now().strftime('%H:%M:%S')
        )
        
        self.send_metals_alert(metal_type, message, api_key)
    
    def send_stop_loss_update_alert(self, metal_type: str, old_sl: float, new_sl: float,
                                    current_price: float, reason: str, potential_pnl_pct: float,
                                    api_key: str = None):
        """Send stop loss update alert"""
        message = self._format_message(
            'stop_loss_updated',
            metal=metal_type,
            old_sl=old_sl,
            new_sl=new_sl,
            current_price=current_price,
            potential_pnl_pct=potential_pnl_pct,
            reason=reason,
            time=datetime.now().strftime('%H:%M:%S')
        )
        
        self.send_metals_alert(metal_type, message, api_key)
    
    def send_signal_alert(self, metal_type: str, signal: str, strength: float,
                          price: float, trend: str, indicators: Dict, api_key: str = None):
        """Send trading signal alert"""
        message = self._format_message(
            'signal_alert',
            metal=metal_type,
            signal=signal,
            strength=strength,
            price=price,
            trend=trend,
            ema_signal=indicators.get('ema', 'N/A'),
            rsi_value=indicators.get('rsi_value', 0),
            rsi_signal=indicators.get('rsi_signal', 'N/A'),
            macd_signal=indicators.get('macd', 'N/A'),
            volume_signal=indicators.get('volume', 'N/A'),
            time=datetime.now().strftime('%H:%M:%S')
        )
        
        self.send_metals_alert(metal_type, message, api_key)
    
    def send_daily_summary(self, date: str, gold_stats: Dict, silver_stats: Dict,
                           total_pnl: float, max_drawdown: float, api_key: str = None):
        """Send daily trading summary"""
        message = self._format_message(
            'daily_summary',
            date=date,
            gold_trades=gold_stats.get('trades', 0),
            gold_win_rate=gold_stats.get('win_rate', 0),
            gold_pnl=gold_stats.get('pnl', 0),
            silver_trades=silver_stats.get('trades', 0),
            silver_win_rate=silver_stats.get('win_rate', 0),
            silver_pnl=silver_stats.get('pnl', 0),
            total_pnl=total_pnl,
            max_drawdown=max_drawdown
        )
        
        self.send_metals_alert('SUMMARY', message, api_key)
    
    def send_error_alert(self, strategy: str, metal_type: str, error_message: str,
                         api_key: str = None):
        """Send error alert"""
        message = self._format_message(
            'error_alert',
            strategy=strategy,
            metal=metal_type,
            error_message=error_message,
            time=datetime.now().strftime('%H:%M:%S')
        )
        
        self.send_metals_alert(metal_type, message, api_key)
    
    def send_strategy_started_alert(self, metal_type: str, strategy_name: str,
                                    symbol: str, exchange: str, stop_loss_type: str,
                                    api_key: str = None):
        """Send strategy started alert"""
        message = self._format_message(
            'strategy_started',
            metal=metal_type,
            strategy_name=strategy_name,
            symbol=symbol,
            exchange=exchange,
            stop_loss_type=stop_loss_type,
            time=datetime.now().strftime('%H:%M:%S')
        )
        
        self.send_metals_alert(metal_type, message, api_key)
    
    def send_strategy_stopped_alert(self, metal_type: str, strategy_name: str,
                                    reason: str, api_key: str = None):
        """Send strategy stopped alert"""
        message = self._format_message(
            'strategy_stopped',
            metal=metal_type,
            strategy_name=strategy_name,
            reason=reason,
            time=datetime.now().strftime('%H:%M:%S')
        )
        
        self.send_metals_alert(metal_type, message, api_key)


# Global instance
metals_alert_service = MetalsAlertService()
