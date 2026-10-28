# 🌅 Aguatech Engineers — IndiaMART AutoBuy Bot Morning Action Plan
**Saved on:** 29-Oct-2026 02:32 AM  
**Project:** Aguatech Engineers Private Limited (AEPL), Pune — Material Handling Equipment (MHE)  
**GitHub Repository:** [https://github.com/yogeshkp85-bit/aguatech-indiamart-autobuy](https://github.com/yogeshkp85-bit/aguatech-indiamart-autobuy)  
**Railway Project:** Active & Running 24/7 (Service Name: `worker`)

---

## 🟢 1. Current System Status (What is Completed)

| Component | Status | Details |
| :--- | :--- | :--- |
| **Core Autobuy Engine** | ✅ Ready | `main_engine.py` (0.5s async high-frequency monitoring) |
| **Product Filter Matrix** | ✅ 100% Verified | 87+ Aguatech MHE catalog keywords + 20 negative keyword guards |
| **Telegram Notifications** | ✅ Ready | Formats and dispatches instant HTML lead alert cards |
| **Local Web CRM Dashboard** | ✅ Ready | Runs on `http://localhost:8501` (`dashboard.py`) |
| **GitHub Remote** | ✅ Pushed | All code committed and synced on `main` branch |
| **Railway Cloud Deployment** | 🟢 **ONLINE** | Worker process is active 24/7 with auto-restart enabled |
| **Safety Controls** | 🛡️ Active | `DRY_RUN_MODE=true` (Zero company credits can be spent) |

---

## 🎯 2. Morning Step-by-Step Checklist (Takes 3 Minutes)

When you have the IndiaMART OTP phone in hand tomorrow morning, follow these exact 4 steps:

### Step 1: Log in to IndiaMART Seller Portal
1. Open Google Chrome.
2. Go to: **[https://seller.indiamart.com/](https://seller.indiamart.com/)**
3. Enter your registered IndiaMART mobile number and type the **OTP** sent to your phone.
4. Make sure you are inside your **Seller Dashboard / BuyLeads** page (where you see "Aguatech Engineers" and your lead list).

---

### Step 2: Copy the Real Session Cookie
*(Note: Session cookies only exist AFTER logging in with OTP).*

**Method A: Using Cookie-Editor Extension (Easiest)**
1. While looking at your logged-in IndiaMART BuyLeads tab, click the **Cookie-Editor** extension icon at the top right of Chrome.
2. Click **Export** ➔ click **Header String**.
3. It will copy the full string to your clipboard.
4. *Verification:* The text should contain IndiaMART keys like `glusr_id=...` or `im_iss=...`.

**Method B: Using Chrome DevTools (Alternative)**
1. On your logged-in IndiaMART BuyLeads page, press **F12**.
2. Click the **Network** tab ➔ filter by **Fetch/XHR** ➔ press **F5** to refresh.
3. Click any request to `seller.indiamart.com`.
4. Under **Request Headers**, copy the full string next to **`Cookie:`**.

---

### Step 3: Paste Cookie into Railway
1. Open your Railway project: **[Railway Dashboard](https://railway.com/)**
2. Click on the **`worker`** service ➔ click the **Variables** tab.
3. Find **`INDIAMART_COOKIE`** (currently showing `pending`).
4. Click edit, paste your copied cookie string, and save.
5. Click the purple **`Deploy`** button at the top-left!

---

### Step 4: Verify in Telegram (Zero Risk)
1. Keep **`DRY_RUN_MODE` = `true`** for the first few hours.
2. The bot will poll IndiaMART every 0.5s. When a buyer posts an inquiry for:
   * *Pallet Trucks (Hand, Hydraulic, Electric, Stainless Steel)*
   * *Stackers (Manual, Semi-Electric, STAKON, Reach Trucks)*
   * *Goods Lifts (Electro-Hydraulic, Cargo Lifts)*
   * *Scissor Lifts (Lift Tables, Mobile Scissor Lifts)*
   * *Drum Handling (Barrel Stackers, Tilters)*
   * *Dock Levelers & Loading Platforms*
3. You will immediately receive a formatted **`[TEST RUN MATCH]`** alert on your Telegram!
4. Once you see that the matches are 100% accurate, simply change **`DRY_RUN_MODE`** to **`false`** in Railway and click **Deploy** to start automatically securing leads before competitors!

---

## 🛠️ Quick Links & Commands Reference

* **Railway Dashboard:** [https://railway.com/](https://railway.com/)
* **GitHub Repository:** [https://github.com/yogeshkp85-bit/aguatech-indiamart-autobuy](https://github.com/yogeshkp85-bit/aguatech-indiamart-autobuy)
* **Local CRM Dashboard:** [http://localhost:8501](http://localhost:8501) (Start anytime with `python dashboard.py`)
* **Run Diagnostics / Test Simulation Locally:**
  ```powershell
  python test_simulator.py
  ```
* **Send Test Telegram Ping:**
  ```powershell
  python tele_alerts.py --test
  ```

---

*Sleep well! Everything is safely backed up and deployed.*
