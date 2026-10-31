"""
Core Asynchronous Runtime Engine for Aguatech Engineers Pvt. Ltd.
High-frequency IndiaMART BuyLead monitoring, tiered priority filtering,
quota management, and automated acquisition with rate-limit protection.
"""

import asyncio
import json
import logging
import os
import random
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
        self.leads_bought_this_week = 0
        self.leads_bought_this_month = 0

        now = datetime.now()
        self.current_date = now.date()
        self.current_week = now.isocalendar()[1]
        self.current_month = now.month

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

        # Human-paced polling interval (default 4.5s prevents high activity blocks)
        self.polling_interval = float(
            os.getenv("POLLING_INTERVAL")
            or settings_cfg.get("polling_interval_seconds", 4.5)
        )
        self.polling_jitter = float(
            os.getenv("POLLING_JITTER")
            or settings_cfg.get("polling_jitter_seconds", 1.0)
        )

        # Budget limits (Daily, Weekly, Monthly)
        self.max_daily_leads = int(
            os.getenv("MAX_LEADS_PER_DAY")
            or settings_cfg.get("max_leads_per_day", 8)
        )
        self.max_weekly_leads = int(
            os.getenv("MAX_LEADS_PER_WEEK")
            or settings_cfg.get("max_leads_per_week", 70)
        )
        self.max_monthly_leads = int(
            os.getenv("MAX_LEADS_PER_MONTH")
            or settings_cfg.get("max_leads_per_month", 300)
        )

        self.proxy_url = (
            os.getenv("INDIAN_PROXY")
            or os.getenv("PROXY_URL")
            or os.getenv("HTTPS_PROXY")
            or os.getenv("HTTP_PROXY")
            or ""
        ).strip().strip("'\"")

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
            "https://seller.indiamart.com/bltxn/?pref=relevant"
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
            "tier": filter_res.tier,
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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://seller.indiamart.com/bltxn/?pref=relevant",
            "Upgrade-Insecure-Requests": "1"
        }

    async def fetch_live_leads(self, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
        """Asynchronously requests the latest BuyLeads feed with anti-block guards."""
        if not self.cookie_string:
            logger.warning("INDIAMART_COOKIE is empty. Pausing live feed polling...")
            await asyncio.sleep(15)
            self.load_configuration()
            return []

        try:
            res = await client.get(self.feed_url, headers=self.build_headers(), follow_redirects=False)

            if res.status_code == 200:
                text = res.text

                # Anti-Rate Limit Guard: Detect IndiaMART's cooldown notice
                if "unusually high activity" in text or "request limit" in text or "Try again in" in text:
                    logger.warning("🟡 [RATE LIMIT NOTICE] IndiaMART requested cooldown. Sleeping for 7.5 minutes...")
                    await self.notifier.send_system_message(
                        "⚠️ <b>IndiaMART Cooldown Notice:</b> High-frequency activity notice detected. "
                        "Bot is automatically pausing for 7.5 minutes to safeguard your seller account."
                    )
                    await asyncio.sleep(450)
                    return []

                leads: List[Dict[str, Any]] = []

                if "window.__BL_DATA__=" in text:
                    try:
                        idx = text.find("window.__BL_DATA__=") + len("window.__BL_DATA__=")
                        data, _ = json.JSONDecoder().raw_decode(text[idx:])
                        display_list = data.get("response", {}).get("DisplayList", [])
                        for item in display_list:
                            city = item.get("GLUSR_CITY") or item.get("GLUSR_USR_CITY") or ""
                            state = item.get("GLUSR_STATE") or item.get("GLUSR_USR_STATE") or ""
                            loc = f"{city}, {state}".strip(", ")
                            is_ver = bool(
                                item.get("GLUSR_USR_ISVERIFIED") in (1, "1", True)
                                or item.get("IS_VERIFIED") in (1, "1", True)
                                or item.get("GLUSR_USR_GST")
                            )
                            leads.append({
                                "id": str(item.get("ETO_OFR_ID") or ""),
                                "subject": item.get("ETO_OFR_TITLE") or item.get("PRIME_MCAT_NAME") or "MHE Requirement",
                                "desc": item.get("ETO_OFR_DESC") or "",
                                "location": loc,
                                "qty": item.get("ETO_OFR_QTY") or 1,
                                "is_verified": is_ver,
                                "buyer_gst": item.get("GLUSR_USR_GST") or "",
                                "approx_value": item.get("ETO_OFR_APPROX_ORDER_VALUE") or "",
                                "time": item.get("BLDATETIME") or "",
                                "raw": item
                            })
                        if leads:
                            return leads
                    except Exception as parse_err:
                        logger.error(f"Error parsing window.__BL_DATA__: {parse_err}")

                try:
                    payload = res.json()
                    if isinstance(payload, dict):
                        return payload.get("leads") or payload.get("data") or payload.get("records") or []
                    elif isinstance(payload, list):
                        return payload
                except Exception:
                    pass

                return leads

            elif res.status_code in (301, 302, 401, 403):
                logger.error(f"🔴 [AUTHENTICATION REQUIRED - HTTP {res.status_code}] IndiaMART requires an active login session!")
                await self.notifier.send_system_message(
                    f"⚠️ <b>CRITICAL ALERT:</b> IndiaMART session cookie is invalid (HTTP {res.status_code})! "
                    "Lead acquisition is paused. Please update session cookie."
                )
                await asyncio.sleep(30)
                self.load_configuration()
                return []

            elif res.status_code == 429:
                logger.warning("🟡 Rate limit detected (HTTP 429). Sleeping for 7 minutes...")
                await self.notifier.send_system_message("⚠️ <b>Rate Limit 429:</b> Sleeping for 7 minutes...")
                await asyncio.sleep(420)
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
        Processes a matching lead with tiered priority and quota budget guards.
        """
        lead_id = str(lead.get("id") or lead.get("glusr_usr_id") or "")
        product = lead.get("subject") or lead.get("title") or "MHE Equipment"
        tier = filter_res.tier
        action = filter_res.action

        quota_str = f"{self.leads_bought_today}/{self.max_daily_leads} today | {self.leads_bought_this_week}/{self.max_weekly_leads} week"

        # Action 1: Tier 3 configured as ALERT_ONLY
        if action == "ALERT_ONLY":
            logger.info(
                f"[TIER {tier} ALERT] Alert-only lead: '{product}' (ID: {lead_id}) in {lead.get('location')} | Matched: {filter_res.matched_keyword}"
            )
            self.record_lead_history(lead, f"ALERT_ONLY_TIER_{tier}", filter_res)
            await self.notifier.send_alert(
                lead=lead,
                is_dry_run=False,
                success=True,
                matched_kw=filter_res.matched_keyword,
                tier=tier,
                action="ALERT_ONLY",
                quota_str=quota_str
            )
            return True

        # Action 2: Check Quota Limits (Daily, Weekly, Monthly)
        if (
            self.leads_bought_today >= self.max_daily_leads
            or self.leads_bought_this_week >= self.max_weekly_leads
            or self.leads_bought_this_month >= self.max_monthly_leads
        ):
            logger.info(
                f"[BUDGET CAP REACHED] Switching to ALERT_ONLY for: '{product}' (ID: {lead_id}). Quota: {quota_str}"
            )
            self.record_lead_history(lead, "QUOTA_CAPPED_ALERT", filter_res)
            await self.notifier.send_alert(
                lead=lead,
                is_dry_run=False,
                success=True,
                matched_kw=filter_res.matched_keyword,
                tier=tier,
                action="QUOTA_REACHED",
                quota_str=quota_str
            )
            return True

        # Action 3: Dry-Run Simulation
        if self.dry_run:
            logger.info(
                f"[DRY-RUN MATCH (Tier {tier})] Would have auto-purchased: '{product}' "
                f"(ID: {lead_id}) in {lead.get('location')} | Matched: {filter_res.matched_keyword}"
            )
            self.record_lead_history(lead, f"DRY_RUN_TIER_{tier}", filter_res)
            await self.notifier.send_alert(
                lead=lead,
                is_dry_run=True,
                success=True,
                matched_kw=filter_res.matched_keyword,
                tier=tier,
                action="BUY",
                quota_str=quota_str
            )
            return True

        # Action 4: LIVE PURCHASE EXECUTION (Consumes real credits)
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
                    self.leads_bought_today += 1
                    self.leads_bought_this_week += 1
                    self.leads_bought_this_month += 1
                    new_quota_str = f"{self.leads_bought_today}/{self.max_daily_leads} today | {self.leads_bought_this_week}/{self.max_weekly_leads} week"
                    logger.info(
                        f"🎉 SUCCESS! Auto-purchased Tier {tier} lead in {latency_ms:.1f}ms: "
                        f"'{product}' (ID: {lead_id}) | Quota: {new_quota_str}"
                    )
                    self.record_lead_history(lead, f"PURCHASED_TIER_{tier}", filter_res)
                    await self.notifier.send_alert(
                        lead=lead,
                        is_dry_run=False,
                        success=True,
                        matched_kw=filter_res.matched_keyword,
                        tier=tier,
                        action="BUY",
                        quota_str=new_quota_str
                    )
                    return True
                else:
                    logger.error(f"Transaction rejected by IndiaMART portal: {res.text}")
                    self.record_lead_history(lead, "FAILED_TRANSACTION", filter_res)
                    await self.notifier.send_alert(
                        lead=lead,
                        is_dry_run=False,
                        success=False,
                        matched_kw=filter_res.matched_keyword,
                        tier=tier,
                        action="BUY",
                        quota_str=quota_str
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
        """Starts the infinite asynchronous monitoring loop with quota resets and anti-detection."""
        print("\n" + "=" * 65)
        print("  AGUATECH ENGINEERS PVT. LTD. - INDIAMART AUTO-BUY SNIPER")
        print("=" * 65)
        print("Company:        Aguatech Engineers Pvt. Ltd. (Pune)")
        print("Sector:         Material Handling Equipment (MHE)")
        print(f"Mode:           {'🟡 DRY-RUN (SIMULATION ONLY)' if self.dry_run else '🚀 LIVE BUY (SPENDS CREDITS)'}")
        print(f"Polling Speed:  Every {self.polling_interval}s (+{self.polling_jitter}s jitter)")
        print(f"Budget Caps:    {self.max_daily_leads}/day | {self.max_weekly_leads}/week | {self.max_monthly_leads}/month")
        print(f"Mobile Account: {self.account_mobile or 'Not configured'}")
        print(f"Session Cookie: {'[CONFIGURED]' if self.cookie_string else '🔴 [MISSING]'}")
        print(f"Telegram Alert: {'[ACTIVE]' if (self.telegram_bot_token and self.telegram_chat_id) else '⚪ [OFFLINE]'}")
        print("=" * 65 + "\n")

        self.is_running = True

        await self.notifier.send_system_message(
            f"🚀 <b>Aguatech Auto-Buy Bot Started!</b>\n"
            f"Mode: {'🟡 Dry-Run (Simulation)' if self.dry_run else '🔴 LIVE PURCHASING'}\n"
            f"Daily Cap: {self.max_daily_leads} leads/day (Weekly: {self.max_weekly_leads})\n"
            f"Polling Cadence: ~{self.polling_interval}s (Anti-detection enabled)"
        )

        timeout = httpx.Timeout(connect=6.0, read=6.0, write=6.0, pool=6.0)
        client_kwargs: Dict[str, Any] = {"timeout": timeout}
        if self.proxy_url:
            client_kwargs["proxy"] = self.proxy_url
            safe_display = self.proxy_url.split("@")[-1] if "@" in self.proxy_url else self.proxy_url
            logger.info(f"🌐 Routing requests via proxy: {safe_display}")

        async with httpx.AsyncClient(**client_kwargs) as client:
            while self.is_running:
                try:
                    now = datetime.now()
                    today = now.date()
                    week = now.isocalendar()[1]
                    month = now.month

                    # Midnight reset for daily quota
                    if today != self.current_date:
                        self.current_date = today
                        self.leads_bought_today = 0
                        logger.info("New day started. Reset daily lead purchase counter to 0.")

                    # Monday morning reset for weekly quota
                    if week != self.current_week:
                        self.current_week = week
                        self.leads_bought_this_week = 0
                        logger.info("New week started. Reset weekly lead purchase counter to 0.")

                    # 1st of month reset for monthly quota
                    if month != self.current_month:
                        self.current_month = month
                        self.leads_bought_this_month = 0
                        logger.info("New month started. Reset monthly lead purchase counter to 0.")

                    leads = await self.fetch_live_leads(client)

                    for lead in leads:
                        lead_id = str(lead.get("id") or lead.get("glusr_usr_id") or "")
                        if not lead_id or lead_id in self.processed_lead_ids:
                            continue

                        self.processed_lead_ids.add(lead_id)
                        res = self.filters.evaluate_lead(lead)
                        if res.passed:
                            await self.execute_buy_action(client, lead, res)
                        else:
                            logger.debug(f"[Skipped] ID {lead_id} ({lead.get('subject')}): {res.rejection_reason}")

                except asyncio.CancelledError:
                    logger.info("Main loop cancelled.")
                    break
                except Exception as loop_err:
                    logger.error(f"Unexpected error in main monitoring loop: {loop_err}")

                # Human jitter sleep
                sleep_dur = self.polling_interval + random.uniform(0.1, self.polling_jitter)
                await asyncio.sleep(sleep_dur)


if __name__ == "__main__":
    bot = AquatechAutomationCore()
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print("\n[Shutdown] Bot stopped safely by user.")
