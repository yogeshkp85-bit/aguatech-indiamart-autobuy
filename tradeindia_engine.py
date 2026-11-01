"""
TradeIndia Automated Lead Acquisition & Inbound Inquiry Engine
Aguatech Engineers Pvt. Ltd. (Pune)

Polls TradeIndia's official Buy Trade Leads & Inquiry APIs,
evaluates leads against Aguatech's product priority matrix,
and dispatches real-time alerts with 1-click WhatsApp links to Telegram.
"""

import asyncio
import json
import logging
import os
import random
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
import httpx
from dotenv import load_dotenv

from product_filters import AguatechFilterEngine, FilterResult
from tele_alerts import TelegramNotifier

# Configure Windows console for UTF-8 compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [TradeIndiaBot] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TradeIndiaBot")


class TradeIndiaEngine:
    """
    Dedicated TradeIndia Lead Automation Engine for Aguatech Engineers.
    Tracks Buy Trade Leads (marketplace RFQs) and Direct Inquiries.
    """

    def __init__(
        self,
        config_path: str = "config.json",
        history_path: str = "tradeindia_history.json"
    ):
        self.config_path = config_path
        self.history_path = history_path
        self.load_configuration()

        self.filters = AguatechFilterEngine(config_dict=self.raw_config, config_path=self.config_path)
        self.notifier = TelegramNotifier(
            bot_token=self.telegram_bot_token,
            chat_id=self.telegram_chat_id,
            config_path=self.config_path
        )

        self.leads_captured_today = 0
        self.inquiries_captured_today = 0
        self.current_date = datetime.now().date()

        self.processed_lead_ids: Set[str] = self.load_lead_history()
        self.is_running = False
        self.last_heartbeat_time = 0.0

    def load_configuration(self) -> None:
        """Loads TradeIndia settings from config.json and .env."""
        load_dotenv(override=True)
        self.raw_config: Dict[str, Any] = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.raw_config = json.load(f)
            except Exception as e:
                logger.error(f"Error loading {self.config_path}: {e}")

        ti_cfg = self.raw_config.get("tradeindia_session", {})
        notify_cfg = self.raw_config.get("notifications", {})
        settings_cfg = self.raw_config.get("system_settings", {})

        self.userid = (os.getenv("TRADEINDIA_USERID") or ti_cfg.get("userid", "17217043")).strip()
        self.profile_id = (os.getenv("TRADEINDIA_PROFILE_ID") or ti_cfg.get("profile_id", "37972693")).strip()
        self.api_key = (os.getenv("TRADEINDIA_KEY") or ti_cfg.get("key", "bf5f5808cd3f1d297e12999bdc0e05c7")).strip()

        self.buy_leads_url = (
            os.getenv("TRADEINDIA_BUY_LEADS_URL")
            or ti_cfg.get("buy_leads_api_url", "https://www.tradeindia.com/utils/my_buy_leads.html")
        ).strip()

        self.inquiry_url = (
            os.getenv("TRADEINDIA_INQUIRY_URL")
            or ti_cfg.get("inquiry_api_url", "https://www.tradeindia.com/utils/my_inquiry.html")
        ).strip()

        self.polling_interval = float(
            os.getenv("TRADEINDIA_POLLING_INTERVAL", "30.0")
        )
        self.max_daily_leads = int(
            os.getenv("TRADEINDIA_MAX_DAILY", "14")
        )

        self.dry_run = os.getenv("DRY_RUN_MODE", "false").lower() in ("true", "1", "yes")

        self.telegram_bot_token = (
            os.getenv("TELEGRAM_BOT_TOKEN") or notify_cfg.get("telegram_bot_token", "")
        ).strip().strip("'\"")

        self.telegram_chat_id = (
            os.getenv("TELEGRAM_CHAT_ID") or notify_cfg.get("telegram_chat_id", "")
        ).strip().strip("'\"")

        self.proxy_url = (
            os.getenv("INDIAN_PROXY")
            or os.getenv("PROXY_URL")
            or os.getenv("HTTPS_PROXY")
            or ""
        ).strip().strip("'\"")

    def load_lead_history(self) -> Set[str]:
        """Loads previously processed lead IDs to prevent duplicate alerts."""
        processed: Set[str] = set()
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            lid = item.get("id") or item.get("lead_id") or item.get("r_id")
                            if lid:
                                processed.add(str(lid))
                logger.info(f"Loaded {len(processed)} previously seen TradeIndia lead IDs.")
            except Exception as e:
                logger.warning(f"Could not load TradeIndia lead history: {e}")
        return processed

    def record_lead_history(self, lead_record: Dict[str, Any]) -> None:
        """Appends processed lead record to local persistent log."""
        try:
            records = []
            if os.path.exists(self.history_path):
                with open(self.history_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
                    if not isinstance(records, list):
                        records = []
            records.append(lead_record)
            if len(records) > 500:
                records = records[-500:]
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to record TradeIndia lead history: {e}")

    async def fetch_direct_inquiries(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """
        Pulls latest inbound inquiries submitted directly to Aguatech product listings.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        yesterday_str = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

        params = {
            "userid": self.userid,
            "profile_id": self.profile_id,
            "key": self.api_key,
            "from_date": yesterday_str,
            "to_date": today_str,
            "limit": 20,
            "page_no": 1
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        }

        try:
            res = await client.get(self.inquiry_url, params=params, headers=headers, timeout=12.0)
            if res.status_code == 200:
                try:
                    payload = res.json()
                    if isinstance(payload, list):
                        return payload
                    elif isinstance(payload, dict):
                        return payload.get("inquiries") or payload.get("data") or []
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"TradeIndia inquiry fetch exception: {e}")
        return []

    async def fetch_buy_trade_leads(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """
        Pulls latest open marketplace Buy Trade Leads matching seller categories.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        yesterday_str = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

        params = {
            "userid": self.userid,
            "profile_id": self.profile_id,
            "key": self.api_key,
            "from_date": yesterday_str,
            "to_date": today_str,
            "limit": 30,
            "page_no": 1
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*"
        }

        try:
            res = await client.get(self.buy_leads_url, params=params, headers=headers, timeout=12.0)
            if res.status_code == 200:
                try:
                    payload = res.json()
                    if isinstance(payload, list):
                        return payload
                    elif isinstance(payload, dict):
                        return payload.get("buy_leads") or payload.get("leads") or payload.get("data") or []
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"TradeIndia buy leads fetch exception: {e}")
        return []

    def format_tradeindia_alert(
        self,
        lead: Dict[str, Any],
        lead_type: str = "BUY_LEAD",
        filter_res: Optional[FilterResult] = None
    ) -> str:
        """Builds a rich Telegram notification with 1-tap WhatsApp chat button."""
        now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        subject = lead.get("product_name") or lead.get("subject") or lead.get("title") or "Material Handling Equipment"
        buyer_name = lead.get("sender_name") or lead.get("contact_person") or lead.get("buyer_name") or "TradeIndia Buyer"
        company = lead.get("company_name") or lead.get("company") or "Direct Buyer"
        city = lead.get("city") or lead.get("location") or "India"
        state = lead.get("state") or ""
        location = f"{city}, {state}".strip(", ")
        mobile = str(lead.get("mobile") or lead.get("phone") or lead.get("sender_mobile") or "").replace("+", "").replace(" ", "").strip()
        email = lead.get("email") or lead.get("sender_email") or "N/A"
        qty = lead.get("quantity") or lead.get("qty") or "1 Unit"
        message = lead.get("inquiry_message") or lead.get("message") or lead.get("desc") or "Buyer RFQ from TradeIndia"
        lead_id = str(lead.get("inquiry_id") or lead.get("r_id") or lead.get("lead_id") or "TI-LEAD")

        tier = filter_res.tier if filter_res else 1
        matched_kw = filter_res.matched_keyword if filter_res else subject

        if lead_type == "DIRECT_INQUIRY":
            header = "⚡ <b>[DIRECT TRADEINDIA INQUIRY - HOT INBOUND LEAD]</b>"
            footer = "🎯 <b>Direct Catalog Inquiry:</b> Buyer contacted Aguatech directly!"
        else:
            header = f"🚀 <b>[TRADEINDIA BUY LEAD (Tier {tier})]</b>"
            footer = f"📊 <b>Quota Used Today:</b> {self.leads_captured_today}/{self.max_daily_leads}"

        # WhatsApp Direct Link
        clean_phone = mobile
        if clean_phone.startswith("91") and len(clean_phone) == 12:
            clean_phone = clean_phone[2:]
        wa_link = f"https://wa.me/91{clean_phone}?text=Hello%20{buyer_name},%20we%20received%20your%20inquiry%20for%20{subject}%20on%20TradeIndia." if clean_phone else ""

        contact_block = ""
        if clean_phone:
            contact_block = f"📱 <b>Mobile:</b> <code>+91 {clean_phone}</code>\n"
        if email and email != "N/A":
            contact_block += f"✉️ <b>Email:</b> {email}\n"

        wa_action = f"\n👉 <a href='{wa_link}'><b>💬 Open WhatsApp Chat with Buyer</b></a>\n" if wa_link else ""

        return (
            f"{header}\n\n"
            f"📦 <b>Product:</b> {subject}\n"
            f"🏷️ <b>Category:</b> <code>{matched_kw}</code> (Tier {tier})\n"
            f"📍 <b>Location:</b> {location}\n"
            f"📊 <b>Required Qty:</b> {qty}\n"
            f"👤 <b>Buyer:</b> {buyer_name} ({company})\n"
            f"{contact_block}"
            f"📝 <b>Requirement:</b> {message[:250]}\n"
            f"🆔 <b>Lead ID:</b> <code>{lead_id}</code>\n"
            f"{wa_action}\n"
            f"{footer}\n"
            f"🕒 <i>{now_str}</i>"
        )

    async def send_heartbeat(self) -> None:
        """Sends periodic pulse to Telegram."""
        now_str = datetime.now().strftime("%d-%b-%Y %I:%M %p")
        text = (
            f"💓 <b>[TRADEINDIA ENGINE PULSE - ACTIVE]</b>\n\n"
            f"🕒 <b>Time:</b> {now_str}\n"
            f"⚡ <b>Status:</b> 🟢 <b>ACTIVELY MONITORING</b>\n"
            f"📊 <b>Leads Captured Today:</b> <b>{self.leads_captured_today} / {self.max_daily_leads}</b>\n"
            f"📬 <b>Direct Inquiries Today:</b> <b>{self.inquiries_captured_today}</b>\n"
            f"🛡️ <b>Mode:</b> {'🟡 Simulation (Dry Run)' if self.dry_run else '🚀 LIVE MONITORING'}\n\n"
            f"✨ <i>TradeIndia lead stream is online and matching with Aguatech MHE catalog.</i>"
        )
        if self.notifier.api_url and self.notifier.chat_id:
            try:
                async with httpx.AsyncClient(timeout=6.0) as client:
                    await client.post(
                        self.notifier.api_url,
                        json={"chat_id": self.notifier.chat_id, "text": text, "parse_mode": "HTML"}
                    )
            except Exception as e:
                logger.error(f"Heartbeat send error: {e}")

    async def start(self) -> None:
        """Main asynchronous polling loop for TradeIndia."""
        print("=" * 65)
        print("Platform:       TradeIndia (MTI Lead Manager)")
        print("Company:        Aguatech Engineers Pvt. Ltd. (Pune)")
        print(f"User ID:        {self.userid} (Profile: {self.profile_id})")
        print(f"Mode:           {'🟡 DRY-RUN' if self.dry_run else '🚀 LIVE MONITORING'}")
        print(f"Polling Speed:  Every {self.polling_interval}s")
        print(f"Daily Cap:      {self.max_daily_leads} leads/day")
        print("=" * 65 + "\n")

        self.is_running = True
        await self.send_heartbeat()

        client_kwargs: Dict[str, Any] = {"timeout": httpx.Timeout(12.0)}
        if self.proxy_url:
            client_kwargs["proxy"] = self.proxy_url

        async with httpx.AsyncClient(**client_kwargs) as client:
            while self.is_running:
                try:
                    now = datetime.now()
                    today = now.date()

                    if today != self.current_date:
                        self.current_date = today
                        self.leads_captured_today = 0
                        self.inquiries_captured_today = 0
                        logger.info("New day. Reset TradeIndia daily counters.")

                    # Heartbeat check every 2 hours
                    current_ts = time.time()
                    if current_ts - self.last_heartbeat_time >= 7200.0:
                        self.last_heartbeat_time = current_ts
                        await self.send_heartbeat()

                    # 1. Fetch Direct Inbound Inquiries
                    inquiries = await self.fetch_direct_inquiries(client)
                    for inq in inquiries:
                        inq_id = str(inq.get("inquiry_id") or inq.get("r_id") or "")
                        if inq_id and inq_id not in self.processed_lead_ids:
                            self.processed_lead_ids.add(inq_id)
                            self.inquiries_captured_today += 1
                            filter_res = self.filters.evaluate_lead(inq)
                            alert_msg = self.format_tradeindia_alert(inq, lead_type="DIRECT_INQUIRY", filter_res=filter_res)
                            await self.notifier.send_system_message(alert_msg)
                            self.record_lead_history({"id": inq_id, "type": "DIRECT_INQUIRY", "time": now.isoformat(), "raw": inq})

                    # 2. Fetch Marketplace Buy Trade Leads
                    buy_leads = await self.fetch_buy_trade_leads(client)
                    for bl in buy_leads:
                        bl_id = str(bl.get("inquiry_id") or bl.get("lead_id") or bl.get("r_id") or "")
                        if bl_id and bl_id not in self.processed_lead_ids:
                            self.processed_lead_ids.add(bl_id)
                            filter_res = self.filters.evaluate_lead(bl)

                            if filter_res.passed:
                                if self.leads_captured_today < self.max_daily_leads:
                                    self.leads_captured_today += 1
                                    alert_msg = self.format_tradeindia_alert(bl, lead_type="BUY_LEAD", filter_res=filter_res)
                                    await self.notifier.send_system_message(alert_msg)
                                    self.record_lead_history({"id": bl_id, "type": "BUY_LEAD", "status": "CAPTURED", "time": now.isoformat(), "raw": bl})
                                else:
                                    logger.info(f"TradeIndia daily cap reached ({self.leads_captured_today}/{self.max_daily_leads}).")

                except asyncio.CancelledError:
                    break
                except Exception as loop_err:
                    logger.error(f"TradeIndia monitoring loop error: {loop_err}")

                sleep_time = self.polling_interval + random.uniform(1.0, 5.0)
                await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    engine = TradeIndiaEngine()
    try:
        asyncio.run(engine.start())
    except KeyboardInterrupt:
        print("\n[Shutdown] TradeIndia Engine stopped safely.")
