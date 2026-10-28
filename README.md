# Aguatech Engineers Pvt. Ltd. — IndiaMART Lead Auto-Buy Platform

A production-grade, sub-second automated lead acquisition engine and CRM dashboard tailored specifically for **Aguatech Engineers Private Limited (AEPL)**, Pune — manufacturer of heavy-duty **Material Handling Equipment (MHE)**.

---

## 🎯 The Problem & Our Solution
* **The Speed Race:** On the IndiaMART marketplace, high-value MHE leads (Pallet Trucks, Stackers, Goods Lifts, Scissor Lifts, Drum Handling) sell out or expire in **seconds**. Competitors using auto-clickers grab them before human operators can even open the page.
* **The Solution:** This engine bypasses browser rendering delays and human reaction time. Running as an asynchronous 24/7 daemon (on your local machine or cloud VPS / Railway), it polls the IndiaMART marketplace feed every **0.5 seconds**, instantly matches incoming leads against Aguatech's product catalog, and executes a sub-second transactional purchase before competitors can react.

---

## 📦 System Architecture & File Structure

```
d:/Indiamart leads Autobuy bot/
├── config.json           # Master config (87+ MHE keywords, negative filters, locations, credentials)
├── product_filters.py    # Sub-millisecond filter & negative keyword rejection engine
├── tele_alerts.py        # Asynchronous Telegram notification engine with rich HTML alerts
├── session_manager.py    # Playwright automated browser login & Chrome F12 manual cookie importer
├── main_engine.py        # High-frequency asynchronous core loop (0.5s polling, buy dispatcher)
├── test_simulator.py     # 10-lead realistic marketplace simulation & diagnostic suite
├── dashboard.py          # Standalone Web Dashboard & Asset Master UI (http://localhost:8501)
├── Procfile              # Railway background worker process definition
├── railway.json          # Railway deployment configuration
├── requirements.txt      # Python dependencies (httpx, beautifulsoup4, playwright, python-dotenv)
├── .env.example          # Environment variables template for cloud deployment
└── .gitignore            # Security protection preventing accidental cookie leakage
```

---

## ⚡ Quick Start in 3 Minutes

### 1. Install Dependencies
Open your terminal in this directory and run:
```bash
pip install -r requirements.txt
```

### 2. Run the Diagnostic Simulator (Zero-Risk Test)
Verify that the filter engine accurately identifies Aguatech MHE equipment and rejects junk inquiries:
```bash
python test_simulator.py
```
*Expected Result: 100% accuracy (6 Aguatech MHE leads accepted, 4 scrap/retail/out-of-state leads rejected).*

### 3. Launch the Web Dashboard & Asset Master
Start your local command center:
```bash
python dashboard.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser. You can:
* View captured leads in real-time in the **Lead CRM**.
* Visually add/remove product keywords in the **Asset Master**.
* Toggle between **Dry-Run Mode** and **Live Autonomous Buying**.
* Send test Telegram alerts with one click.

---

## 📱 Telegram Alerts Setup (Personal or Group)

1. Open Telegram and search for **`@BotFather`**.
2. Send `/newbot`, name your bot (e.g., `AguatechLeadBot`), and copy the **HTTP API Token** (e.g., `73829104:AAHj...`).
3. To get your personal ID: Search for **`@userinfobot`** and click Start. Copy your **Id** number (e.g., `987654321`).
4. To test your connection immediately:
   * Paste the Token and Chat ID into `config.json` or your `.env` file.
   * Run:
     ```bash
     python tele_alerts.py --test
     ```
   * You will receive an instant test alert on your smartphone!

---

## 🔐 IndiaMART Session Cookie Setup

The bot requires an active session token to query IndiaMART's internal BuyLeads feed. You have two easy methods:

### Method A: Automated Browser Login (Playwright)
Run the automated session manager:
```bash
playwright install chromium
python session_manager.py
```
A browser window will open. Enter your IndiaMART registered mobile number, submit the OTP, and the script will automatically intercept your session cookies and save them to `config.json` and `.env`.

### Method B: Manual Copy from Chrome DevTools (Fastest)
1. Open Google Chrome Incognito.
2. Log into `https://seller.indiamart.com/` and navigate to the **BuyLeads** feed.
3. Press **F12** -> Click **Network** tab -> Select **Fetch/XHR**.
4. Refresh the page. Click on any request loading leads.
5. Under **Request Headers**, copy the entire string after `Cookie:`.
6. Run:
   ```bash
   python session_manager.py --manual
   ```
   Paste your cookie string when prompted. It saves automatically!

---

## 🚀 24/7 Cloud Deployment on Railway

Deploying on Railway ensures your bot runs 24/7 even when your personal computer is turned off.

### Step 1: Push to GitHub
Create a private repository on GitHub (e.g. `aguatech-indiamart-autobuy`) and push this folder:
```bash
git init
git add .
git commit -m "Aguatech IndiaMART AutoBuy Bot initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/aguatech-indiamart-autobuy.git
git push -u origin main
```
*(Note: `.gitignore` protects your real cookies and credentials from ever being published).*

### Step 2: Deploy on Railway
1. Log into **[Railway.app](https://railway.app)**.
2. Click **New Project** -> **Deploy from GitHub repo** -> Select your repository.
3. Railway will detect the `Procfile` and `requirements.txt` and launch the worker daemon.

### Step 3: Add Variables in Railway Dashboard
In your Railway project service, go to **Variables** and add:
| Variable Name | Value Example | Description |
|---|---|---|
| `DRY_RUN_MODE` | `true` | Keep `true` for first 24h testing! Change to `false` when ready to buy. |
| `ACCOUNT_MOBILE` | `9876543210` | Registered IndiaMART mobile number |
| `INDIAMART_COOKIE` | *(Your Cookie String)* | Extracted session cookie header |
| `TELEGRAM_BOT_TOKEN` | `73829104:AAHj...` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | `987654321` | Your personal or group Telegram Chat ID |
| `POLLING_INTERVAL` | `0.5` | Polling speed in seconds (2 requests / second) |
| `MAX_LEADS_PER_DAY` | `15` | Daily cap to protect company wallet |

Railway will automatically restart your bot with the new variables and run continuously with automatic recovery!

---

## 🛡️ Safety & Wallet Protection Safeguards

1. **Dry-Run Mode Default:** By default, `DRY_RUN_MODE` is enabled. The bot catches matching leads, formats Telegram alerts, and logs records without expending any real IndiaMART credits.
2. **Negative Keyword Guard:** Automatically rejects inquiries containing keywords like `"second hand"`, `"used"`, `"scrap"`, `"repair only"`, `"toy"`, and `"mineral water plant"` (preventing confusion with "Agua").
3. **Daily Cap:** Enforces `MAX_LEADS_PER_DAY` (e.g., 15 leads) to prevent an unexpected flood of leads from burning the company credit wallet.
4. **Deduplication Engine:** In-memory set and persistent `leads_history.json` guarantee that no lead is ever processed or purchased twice.

---

## 🏭 Aguatech Engineers MHE Product Catalog Coverage
* **Pallet Trucks:** Hand Pallet, Hydraulic Pallet, Electric, Semi-Electric, Low Profile, High Lift, Reel/Paper Roll Carrier, Stainless Steel.
* **Stackers & Reach Trucks:** Manual Stacker, Semi-Electric, Battery Operated, Electric Stacker, Reach Truck, Electric Forklift, STAKON series.
* **Goods Lifts & Elevators:** Electro-Hydraulic Goods Lift, Industrial Cargo Lift, Freight Elevator, Wall Mounted Lift, VRC Conveyors.
* **Scissor Lifts & Tables:** Hydraulic Scissor Lift, Scissor Lift Table, Mobile Scissor Lift, Powered Lift Table, Die Loader.
* **Drum Handling:** Drum Stacker, Barrel Lifter, Drum Tilter, Barrel Stacker-cum-Tilter, Drum Grabber, Drum Shifter.
* **Dock Equipment:** Hydraulic Dock Leveler, Mechanical Dock Leveler, Mobile Dock Ramp, Loading/Unloading Platform.
* **Aerial Work Platforms:** High Lift Maintenance Platform, Articulated Boom, Telescopic Boom, Aluminium Hydraulic Ladder.
