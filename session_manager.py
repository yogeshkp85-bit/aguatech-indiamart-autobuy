"""
Session & Cookie Manager for IndiaMART Seller Portal
Extracts, validates, and stores session authentication cookies for Aguatech Engineers.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Dict, Optional

# Configure Windows console for UTF-8 compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logger = logging.getLogger("AguatechBot.Session")


class PlaywrightSessionManager:
    """
    Automates IndiaMART authentication and cookie extraction using Playwright.
    Also provides a manual import utility for quick setup without browser automation.
    """

    def __init__(self, config_path: str = "config.json", env_path: str = ".env"):
        self.config_path = config_path
        self.env_path = env_path
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

    def load_config(self) -> Dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_cookie_to_config(self, cookie_str: str) -> None:
        """Saves the extracted cookie string to config.json."""
        data = self.load_config()
        if "indiamart_session" not in data:
            data["indiamart_session"] = {}
        data["indiamart_session"]["cookie_string"] = cookie_str
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved cookie string to {self.config_path}")

    def save_cookie_to_env(self, cookie_str: str) -> None:
        """Appends or updates the INDIAMART_COOKIE entry in .env."""
        try:
            lines = []
            updated = False
            if os.path.exists(self.env_path):
                with open(self.env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                for i, line in enumerate(lines):
                    if line.startswith("INDIAMART_COOKIE="):
                        lines[i] = f'INDIAMART_COOKIE="{cookie_str}"\n'
                        updated = True
                        break

            if not updated:
                lines.append(f'\nINDIAMART_COOKIE="{cookie_str}"\n')

            with open(self.env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            logger.info(f"Updated INDIAMART_COOKIE in {self.env_path}")
        except Exception as e:
            logger.warning(f"Could not update .env file: {e}")

    async def launch_interactive_login(self) -> str:
        """
        Spins up a Chromium browser window so the user can log into IndiaMART
        with their registered mobile number and OTP. Intercepts cookies on success.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error(
                "Playwright is not installed. Run: pip install playwright && playwright install chromium\n"
                "Or use manual cookie import: python session_manager.py --manual"
            )
            return ""

        print("\n" + "=" * 65)
        print("  INDIAMART INTERACTIVE LOGIN (AGUATECH AUTO-BUY ENGINE)")
        print("=" * 65)
        print("1. A Chromium browser window will open.")
        print("2. Enter your registered IndiaMART mobile number.")
        print("3. Enter the OTP sent to your phone.")
        print("4. Once you reach the Seller Dashboard/BuyLeads page,")
        print("   your session cookies will be captured automatically!")
        print("=" * 65 + "\n")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(user_agent=self.user_agent)
            page = await context.new_page()

            logger.info("Opening IndiaMART Seller Login portal...")
            await page.goto("https://seller.indiamart.com/", wait_until="domcontentloaded")

            print("\n>> Please complete login / OTP verification in the browser window now...")
            print(">> Waiting up to 180 seconds for successful authentication...")

            try:
                # Wait until redirected to any seller dashboard or buyleads page
                await page.wait_for_url(
                    lambda url: any(x in url.lower() for x in ["buyleads", "dashboard", "blapi", "leadmanager"]),
                    timeout=180000
                )
                print("\nLogin detected! Extracting session tokens...")
                # Small wait to ensure cookies are populated
                await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"Timed out or navigation occurred: {e}. Attempting cookie extraction anyway...")

            cookies = await context.cookies()
            cookie_string = "; ".join([f"{c['name']}={c['value']}" for c in cookies if c.get("name") and c.get("value")])
            await browser.close()

            if cookie_string:
                self.save_cookie_to_config(cookie_string)
                self.save_cookie_to_env(cookie_string)
                print("\n" + "=" * 65)
                print("SUCCESS: Session cookies extracted & saved!")
                print("You can now start the main bot with: python main_engine.py")
                print("=" * 65 + "\n")
                return cookie_string
            else:
                logger.error("No cookies were captured from the browser session.")
                return ""

    def manual_cookie_import(self) -> str:
        """
        CLI utility to paste raw Cookie header copied from Chrome DevTools (F12).
        """
        print("\n" + "=" * 65)
        print("  MANUAL COOKIE IMPORT (CHROME DEVTOOLS)")
        print("=" * 65)
        print("1. Open Chrome Incognito -> Login to https://seller.indiamart.com/")
        print("2. Go to the 'BuyLeads' feed page.")
        print("3. Press F12 -> Network Tab -> Filter 'Fetch/XHR'.")
        print("4. Refresh the page, click any request (e.g. leads/buyleads).")
        print("5. Under 'Request Headers', copy the value of 'Cookie:'.")
        print("=" * 65)

        cookie_str = input("\nPaste the full Cookie string here:\n").strip()
        if not cookie_str:
            print("Import cancelled: Empty cookie string.")
            return ""

        # Remove surrounding quotes if accidentally included
        if (cookie_str.startswith('"') and cookie_str.endswith('"')) or (cookie_str.startswith("'") and cookie_str.endswith("'")):
            cookie_str = cookie_str[1:-1]

        self.save_cookie_to_config(cookie_str)
        self.save_cookie_to_env(cookie_str)

        print("\n" + "=" * 65)
        print("SUCCESS! Cookie saved to config.json and .env.")
        print("If deploying to Railway, copy this cookie and set INDIAMART_COOKIE variable.")
        print("=" * 65 + "\n")
        return cookie_str


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="IndiaMART Session & Cookie Manager")
    parser.add_argument("--manual", action="store_true", help="Manually paste cookies from Chrome DevTools")
    args = parser.parse_args()

    manager = PlaywrightSessionManager()
    if args.manual:
        manager.manual_cookie_import()
    else:
        try:
            asyncio.run(manager.launch_interactive_login())
        except KeyboardInterrupt:
            print("\nAborted by user.")
        except Exception as err:
            logger.error(f"Error launching interactive browser: {err}")
            print("\nTip: You can use manual cookie import by running:")
            print("  python session_manager.py --manual")
