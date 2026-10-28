"""
Telegram Alert Dispatcher for Aguatech Engineers Pvt. Ltd.
Sends real-time lead purchase notifications to personal chats or sales groups.
"""

import asyncio
import html
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("AguatechBot.Notifier")


class TelegramNotifier:
    """
    Asynchronous notification manager for Telegram.
    Pushes sub-second alerts to mobile devices when a lead is spotted or purchased.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        config_path: str = "config.json"
    ):
        self.config_path = config_path
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        # Fallback to config.json if environment variables are not populated
        if (not self.bot_token or not self.chat_id) and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                notify_cfg = cfg.get("notifications", {})
                self.bot_token = self.bot_token or notify_cfg.get("telegram_bot_token")
                self.chat_id = self.chat_id or notify_cfg.get("telegram_chat_id")
            except Exception as e:
                logger.error(f"[Telegram Notifier] Failed to read config: {e}")

        # Normalize token string (strip any accidental whitespaces or quotes)
        if self.bot_token:
            self.bot_token = str(self.bot_token).strip().strip("'\"")
        if self.chat_id:
            self.chat_id = str(self.chat_id).strip().strip("'\"")

        self.api_url = (
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            if self.bot_token
            else None
        )

        if not self.bot_token or not self.chat_id:
            logger.warning(
                "[Telegram Notifier] Credentials incomplete. Alerts will be logged to console only. "
                "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env or Railway variables."
            )
        else:
            logger.info(f"[Telegram Notifier] Configured with Chat ID: {self.chat_id}")

    @staticmethod
    def _escape_html(text: Any) -> str:
        """Sanitizes text for Telegram HTML mode."""
        return html.escape(str(text or ""))

    def format_alert_message(
        self,
        lead: Dict[str, Any],
        is_dry_run: bool = False,
        success: bool = True,
        matched_kw: Optional[str] = None
    ) -> str:
        """Builds a rich, professional HTML message for the Telegram alert."""
        timestamp = datetime.now().strftime("%d-%b-%Y %I:%M:%S %p")
        subject = self._escape_html(lead.get("subject") or lead.get("title") or "Industrial MHE Inquiry")
        location = self._escape_html(lead.get("location") or lead.get("city") or "India")
        qty = self._escape_html(lead.get("qty") or lead.get("quantity") or "1")
        desc = self._escape_html(lead.get("desc") or lead.get("description") or "Direct buyer RFQ from IndiaMART.")
        lead_id = self._escape_html(lead.get("id") or lead.get("glusr_usr_id") or "N/A")
        kw = self._escape_html(matched_kw or "MHE Equipment")

        # Truncate description if too long
        if len(desc) > 300:
            desc = desc[:300] + "..."

        if is_dry_run:
            header = "🟡 <b>[TEST RUN MATCH - DRY RUN]</b>"
            footer = "⚠️ <i>Simulation mode active. No IndiaMART credits were deducted.</i>"
        elif success:
            header = "🚀 <b>[AGUATECH MHE LEAD AUTO-BOUGHT]</b>"
            footer = "✅ <b>Lead purchased in fraction of second! Details unlocked in Seller Panel.</b>"
        else:
            header = "❌ <b>[AGUATECH LEAD PURCHASE FAILED]</b>"
            footer = "⚠️ <i>API purchase request failed. Check cookies and credit balance.</i>"

        msg = (
            f"{header}\n\n"
            f"📦 <b>Product:</b> {subject}\n"
            f"🏷️ <b>Matched Category:</b> <code>{kw}</code>\n"
            f"📍 <b>Location:</b> {location}\n"
            f"📊 <b>Required Quantity:</b> {qty} Unit(s)\n"
            f"🆔 <b>Lead ID:</b> <code>{lead_id}</code>\n"
            f"⏰ <b>Captured At:</b> {timestamp}\n\n"
            f"📝 <b>Buyer Requirement:</b>\n"
            f"<blockquote>{desc}</blockquote>\n\n"
            f"{footer}\n\n"
            f"🔗 <a href='https://seller.indiamart.com/leadmanager/'>Open IndiaMART Lead Manager</a>"
        )
        return msg

    async def send_alert(
        self,
        lead: Dict[str, Any],
        is_dry_run: bool = False,
        success: bool = True,
        matched_kw: Optional[str] = None
    ) -> bool:
        """Sends an instant lead alert to the configured Telegram chat."""
        if not self.api_url or not self.chat_id:
            logger.info(
                f"[Alert Simulated] {lead.get('subject')} | DryRun={is_dry_run} | (Telegram token not set)"
            )
            return False

        message = self.format_alert_message(
            lead=lead,
            is_dry_run=is_dry_run,
            success=success,
            matched_kw=matched_kw
        )

        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(self.api_url, json=payload)
                if res.status_code == 200:
                    logger.info("[Telegram Notifier] Alert sent successfully!")
                    return True
                else:
                    logger.error(f"[Telegram Notifier] Telegram API error ({res.status_code}): {res.text}")
                    return False
        except Exception as e:
            logger.error(f"[Telegram Notifier] Failed to dispatch Telegram alert: {e}")
            return False

    async def send_system_message(self, text: str) -> bool:
        """Sends a high-priority system status notification (e.g. startup, cookie expired)."""
        if not self.api_url or not self.chat_id:
            logger.info(f"[System Notice] {text}")
            return False

        payload = {
            "chat_id": self.chat_id,
            "text": f"🤖 <b>[Aguatech Bot System]</b>\n\n{text}",
            "parse_mode": "HTML"
        }

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(self.api_url, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"[Telegram Notifier] System message error: {e}")
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def test():
        notifier = TelegramNotifier()
        if "--test" in sys.argv:
            print("\nSending test ping to Telegram...")
            mock_lead = {
                "id": "TEST_BL_9999",
                "subject": "Hydraulic Scissor Lift Table 1000kg",
                "location": "Pune, Maharashtra",
                "qty": 2,
                "desc": "Looking for electric scissor lift table for assembly line at Bhosari MIDC Pune."
            }
            ok = await notifier.send_alert(mock_lead, is_dry_run=True, matched_kw="scissor lift")
            print(f"Test alert result: {'SUCCESS' if ok else 'FAILED (Check credentials in .env/config.json)'}")
        else:
            print("Telegram Notifier initialized. Use 'python tele_alerts.py --test' to verify connectivity.")

    asyncio.run(test())
