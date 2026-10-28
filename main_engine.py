"""
Core Asynchronous Runtime Engine for Aguatech Engineers Pvt. Ltd.
High-frequency IndiaMART BuyLead monitoring, sub-second filtering, and automated acquisition.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import httpx

# Configure Windows console for UTF-8 compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Try loading .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from product_filters import AguatechFilterEngine, FilterResult
from tele_alerts import TelegramNotifier

# Configure structured console logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AguatechBot.Core")


class AquatechAutomationCore:
    """
    Main runtime daemon. Coordinates continuous background polling,
    instant filter validation, sub-second transactional buying, and alert dispatching.
    """

    def __init__(self, config_path: str = "config.json", history_path: str = "leads_history.json"):
        self.config_path = config_path
        self.history_path = history_path
        self.load_configuration()

        self.filters = AguatechFilterEngine(config_dict=self.raw_config, config_path=self.config_path)
        self.notifier = TelegramNotifier(
            bot_token=self.telegram_bot_token,
            chat_id=self.telegram_chat_id,
            config_path=self.config_path
        )

        self.leads_bought_today = 0
        self.current_date = datetime.now().date()
        self.processed_lead_ids: Set[str] = self.load_lead_history()
        self.is_running = False

    def load_configuration(self) -> None:
        """Reads configuration with environment variable precedence."""
        self.raw_config: Dict[str, Any] = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.raw_config = json.load(f)
            except Exception as e:
                logger.error(f"Error loading {self.config_path}: {e}")

        session_cfg = self.raw_config.get("indiamart_session", {})
        notify_cfg = self.raw_config.get("notifications", {})
        settings_cfg = self.raw_config.get("system_settings", {})

        # Environment variables take precedence (vital for Railway deployment)
        self.cookie_string = (
            os.getenv("INDIAMART_COOKIE")
            or session_cfg.get("cookie_string", "")
        ).strip().strip("'\"")

        self.account_mobile = (
            os.getenv("ACCOUNT_MOBILE")
            or session_cfg.get("account_mobile", "")
        ).strip().strip("'\"")

        self.user_agent = (
            os.getenv("USER_AGENT")
            or session_cfg.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        ).strip()

        # Operational flags
        dry_run_env = os.getenv("DRY_RUN_MODE")
        if dry_run_env is not None:
            self.dry_run = dry_run_env.lower() in ("true", "1", "yes")
        else:
            self.dry_run = bool(settings_cfg.get("dry_run_mode", True))

        self.polling_interval = float(
            os.getenv("POLLING_INTERVAL")
            or settings_cfg.get("polling_interval_seconds", 0.5)
        )

        self.max_daily_leads = int(
            os.getenv("MAX_LEADS_PER_DAY")
            or settings_cfg.get("max_leads_per_day", 15)
        )

        # Telegram credentials
        self.telegram_bot_token = (
            os.getenv("TELEGRAM_BOT_TOKEN")
            or notify_cfg.get("telegram_bot_token", "")
        ).strip().strip("'\"")

        self.telegram_chat_id = (
            os.getenv("TELEGRAM_CHAT_ID")
            or notify_cfg.get("telegram_chat_id", "")
        ).strip().strip("'\"")

        # IndiaMART Internal Endpoints
        self.feed_url = os.getenv(
            "FEED_URL",
            "https://seller.indiamart.com/blapi/v1/buyleads"
        )
        self.consume_url = os.getenv(
            "BUY_URL",
            "https://seller.indiamart.com/blapi/v1/consume"
        )

    def load_lead_history(self) -> Set[str]:
        """Loads previously processed lead IDs to prevent duplicate buys."""
        processed: Set[str] = set()
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            lid = item.get("id") or item.get("lead_id")
                            if lid:
                                processed.add(str(lid))
                logger.info(f"Loaded {len(processed)} previously seen lead IDs from history.")
            except Exception as e:
                logger.warning(f"Could not load lead history: {e}")
        return processed

    def record_lead_history(self, lead: Dict[str, Any], status: str, filter_res: FilterResult) -> None:
        """Appends processed lead record to local persistent log."""
        record = {
            "timestamp": datetime.now().isoformat(),
            "id": str(lead.get("id", "N/A")),
            "subject": lead.get("subject", "N/A"),
            "location": lead.get("location", "N/A"),
            "qty": lead.get("qty", 1),
            "status": status,
            "matched_keyword": filter_res.matched_keyword,
            "matched_location": filter_res.matched_location,
            "rejection_reason": filter_res.rejection_reason
        }
        try:
            records = []
            if os.path.exists(self.history_path):
                with open(self.history_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
                    if not isinstance(records, list):
                        records = []
            records.append(record)
            # Keep only last 500 records to prevent file bloat
            if len(records) > 500:
                records = records[-500:]
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to append lead history: {e}")

    def build_headers(self) -> Dict[str, str]:
        """Constructs headers to mirror a legitimate logged-in browser session."""
        return {
            "User-Agent": self.user_agent,
            "Cookie": self.cookie_string,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://seller.indiamart.com/buyleads/",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }

    async def fetch_live_leads(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """Asynchronously requests the latest BuyLeads feed."""
        if not self.cookie_string:
            logger.warning(
                "INDIAMART_COOKIE is empty. Pausing live feed polling (waiting for valid session cookie)... "
                "Run 'python session_manager.py' or 'python test_simulator.py'."
            )
            await asyncio.sleep(15)
            # Re-read configuration in case cookie was added via dashboard or .env
            self.load_configuration()
            return []

        try:
            res = await client.get(self.feed_url, headers=self.build_headers(), follow_redirects=False)

            if res.status_code == 200:
                try:
                    payload = res.json()
                    # IndiaMART payload structures: {"leads": [...]}, {"data": [...]}, or array
                    if isinstance(payload, dict):
                        return payload.get("leads") or payload.get("data") or payload.get("records") or []
                    elif isinstance(payload, list):
                        return payload
                    return []
                except Exception as json_err:
                    logger.error(f"Error parsing feed JSON: {json_err}")
                    return []

            elif res.status_code in (301, 302, 401, 403):
                logger.error(
                    f"🔴 [AUTHENTICATION REQUIRED - HTTP {res.status_code}] IndiaMART requires an active login session! "
                    "Session cookie is missing, expired, or redirected to login. "
                    "Run 'python session_manager.py' or update INDIAMART_COOKIE."
                )
                await self.notifier.send_system_message(
                    f"⚠️ <b>CRITICAL ALERT:</b> IndiaMART session cookie is invalid (HTTP {res.status_code})! "
                    "Lead acquisition is paused. Please update session cookie."
                )
                await asyncio.sleep(30)
                # Re-read configuration in case cookie was updated
                self.load_configuration()
                return []

            elif res.status_code == 429:
                logger.warning("🟡 Rate limit detected (HTTP 429). Backing off for 10 seconds...")
                await asyncio.sleep(10)
                return []

            else:
                logger.warning(f"Unexpected feed response status: {res.status_code}")
                return []

        except httpx.RequestError as net_err:
            logger.warning(f"Network connection glitch: {net_err}. Retrying...")
            return []

    async def execute_buy_action(
        self,
        client: httpx.AsyncClient,
        lead: Dict[str, Any],
        filter_res: FilterResult
    ) -> bool:
        """
        Sends the sub-second transactional POST request to purchase the lead.
        Guarded by Dry-Run mode.
        """
        lead_id = str(lead.get("id") or lead.get("glusr_usr_id") or "")
        product = lead.get("subject") or lead.get("title") or "MHE Equipment"

        if self.dry_run:
            logger.info(
                f"[DRY-RUN MATCH] Would have auto-purchased: '{product}' "
                f"(ID: {lead_id}) in {lead.get('location')} | Matched: {filter_res.matched_keyword}"
            )
            self.record_lead_history(lead, "DRY_RUN_MATCH", filter_res)
            await self.notifier.send_alert(
                lead=lead,
                is_dry_run=True,
                success=True,
                matched_kw=filter_res.matched_keyword
            )
            return True

        # LIVE PURCHASE EXECUTION (Consumes real credits)
        payload = {
            "lead_id": lead_id,
            "mobile": self.account_mobile,
            "action": "consume",
            "source": "api"
        }

        try:
            start_t = time.perf_counter()
            res = await client.post(self.consume_url, headers=self.build_headers(), data=payload)
            latency_ms = (time.perf_counter() - start_t) * 1000

            if res.status_code == 200:
                data = res.json()
                if data.get("status") in ("success", "ok", 1) or data.get("code") == 200:
                    logger.info(
                        f"🎉 SUCCESS! Auto-purchased lead in {latency_ms:.1f}ms: "
                        f"'{product}' (ID: {lead_id})"
                    )
                    self.leads_bought_today += 1
                    self.record_lead_history(lead, "PURCHASED", filter_res)
                    await self.notifier.send_alert(
                        lead=lead,
                        is_dry_run=False,
                        success=True,
                        matched_kw=filter_res.matched_keyword
                    )
                    return True
                else:
                    logger.error(f"Transaction rejected by IndiaMART portal: {res.text}")
                    self.record_lead_history(lead, "FAILED_TRANSACTION", filter_res)
                    await self.notifier.send_alert(
                        lead=lead,
                        is_dry_run=False,
                        success=False,
                        matched_kw=filter_res.matched_keyword
                    )
                    return False
            else:
                logger.error(f"HTTP {res.status_code} while purchasing lead: {res.text}")
                self.record_lead_history(lead, "HTTP_ERROR", filter_res)
                return False

        except Exception as e:
            logger.error(f"Critical execution error during lead purchase: {e}")
            self.record_lead_history(lead, "EXCEPTION_ERROR", filter_res)
            return False

    async def start(self) -> None:
        """Starts the infinite asynchronous monitoring loop."""
        print("\n" + "=" * 65)
        print("  AGUATECH ENGINEERS PVT. LTD. - INDIAMART AUTO-BUY SNIPER")
        print("=" * 65)
        print(f"Company:        Aguatech Engineers Pvt. Ltd. (Pune)")
        print(f"Sector:         Material Handling Equipment (MHE)")
        print(f"Mode:           {'🟡 DRY-RUN (SIMULATION ONLY)' if self.dry_run else '🚀 LIVE BUY (SPENDS CREDITS)'}")
        print(f"Polling Speed:  Every {self.polling_interval}s")
        print(f"Daily Cap:      {self.max_daily_leads} leads/day")
        print(f"Mobile Account: {self.account_mobile or 'Not configured'}")
        print(f"Session Cookie: {'[CONFIGURED]' if self.cookie_string else '🔴 [MISSING - Run session_manager.py]'}")
        print(f"Telegram Alert: {'[ACTIVE]' if (self.telegram_bot_token and self.telegram_chat_id) else '⚪ [OFFLINE]'}")
        print("=" * 65 + "\n")

        if not self.cookie_string:
            logger.warning(
                "INDIAMART_COOKIE is empty. Live feed fetching requires a valid session. "
                "You can run the simulator to test matching without cookies: python test_simulator.py"
            )

        self.is_running = True
        await self.notifier.send_system_message(
            f"🚀 <b>Aguatech Auto-Buy Bot Started!</b>\n"
            f"Mode: {'🟡 Dry-Run' if self.dry_run else '🔴 Live Purchasing'}\n"
            f"Daily Cap: {self.max_daily_leads} leads\n"
            f"Polling: Every {self.polling_interval}s"
        )

        timeout = httpx.Timeout(connect=3.0, read=4.0, write=4.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            while self.is_running:
                try:
                    # Midnight reset for daily quota
                    today = datetime.now().date()
                    if today != self.current_date:
                        self.current_date = today
                        self.leads_bought_today = 0
                        logger.info("New day started. Reset daily lead purchase counter to 0.")

                    # Budget limit guard
                    if self.leads_bought_today >= self.max_daily_leads:
                        logger.info(
                            f"Daily lead budget limit reached ({self.leads_bought_today}/{self.max_daily_leads}). "
                            "Pausing acquisition until tomorrow..."
                        )
                        await asyncio.sleep(3600)
                        continue

                    leads = await self.fetch_live_leads(client)

                    for lead in leads:
                        lead_id = str(lead.get("id") or lead.get("glusr_usr_id") or "")
                        if not lead_id or lead_id in self.processed_lead_ids:
                            continue

                        # Mark seen immediately
                        self.processed_lead_ids.add(lead_id)

                        # Evaluate against Aguatech MHE catalog & negative filters
                        res = self.filters.evaluate_lead(lead)
                        if res.passed:
                            await self.execute_buy_action(client, lead, res)
                        else:
                            logger.debug(
                                f"[Skipped] ID {lead_id} ({lead.get('subject')}): {res.rejection_reason}"
                            )

                except asyncio.CancelledError:
                    logger.info("Main loop cancelled.")
                    break
                except Exception as loop_err:
                    logger.error(f"Unexpected error in main monitoring loop: {loop_err}")

                await asyncio.sleep(self.polling_interval)


if __name__ == "__main__":
    bot = AquatechAutomationCore()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\n[Shutdown] Bot stopped safely by user.")
