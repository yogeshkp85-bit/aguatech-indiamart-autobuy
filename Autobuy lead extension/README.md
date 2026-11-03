# IndiaMart Lead Autoclick Pro (Chrome Extension)

An automated BuyLead matching and contact engine built specifically for sellers using `seller.indiamart.com`. It monitors incoming BuyLeads in real-time, evaluates them against your custom product keywords, quantity thresholds, location criteria, and verification badges, and safely executes "Contact Buyer Now" clicks.

---

## 🚀 Key Capabilities

- **Automatic BuyLead Detection**: Analyzes DOM cards on `seller.indiamart.com/bl/` and identifies title, quantity, order value, buyer location, export country, and verification status.
- **Rule Matching Engine**:
  - **Keywords**: Singular/plural matching, pharma term matching (e.g. *strip / stripe*), minimum quantity requirements, and target units.
  - **Click Limits**: Per-keyword click limits and global daily click ceilings (resets automatically at midnight).
  - **Location & Export Filtering**: Normal domestic states/cities whitelist, blocked states blacklist, and international export country targeting.
  - **Exclusions**: Excludes "Buyer also viewed" recommendations, negative keywords (e.g. *scrap, hire, second hand*), and retail/single-piece inquiries.
  - **Buyer Verifications**: Click only leads with GST, Mobile, Email, WhatsApp, or TrustSEAL badges.
- **Human-like Automation**: Natural delays (800ms - 1500ms) with smooth scroll simulation to prevent marketplace bot flags.
- **Audio Chime & Visual HUD**: In-browser audio notification when a lead is captured, along with an on-screen live auto-refresh timer HUD.
- **Bulk CSV Import & Export**: Import UTF-8/UTF-16 CSV files for keywords, locations, categories, and countries with automatic detection of Excel `.xlsx` files.
- **Built-in Lead Simulator**: Test any lead requirement against your configured rules right in the extension dashboard before going live.

---

## 📦 How to Load in Google Chrome / Brave / Edge

1. Open your browser and navigate to: `chrome://extensions/`
2. Enable **"Developer mode"** (toggle in the top-right corner).
3. Click the **"Load unpacked"** button in the top-left corner.
4. Select this project folder:
   ```
   e:\CRM and Gmail outreach\Autobuy lead extension
   ```
5. The extension **IndiaMart Lead Autoclick Pro** is now installed! Pin it to your toolbar for quick access.

---

## 🛠️ Folder Structure

```
├── manifest.json            # Manifest V3 extension configuration
├── background.js           # Service worker handling midnight resets & badge counters
├── content/
│   ├── content.js          # Core scanning loop, auto-refresh countdown, and clicker
│   ├── parser.js           # Multi-strategy DOM card extractor for IndiaMart
│   ├── matcher.js          # Comprehensive rule matching and filtering logic
│   └── content.css         # Floating HUD overlay, matched lead styling, and toasts
├── popup/
│   ├── popup.html          # Quick toolbar popup interface
│   ├── popup.js            # Popup controller
│   └── popup.css           # Modern dark-mode popup styles
├── dashboard/
│   ├── dashboard.html      # Full-page advanced rules and analytics dashboard
│   ├── dashboard.js        # Dashboard controller with rule tables & CSV handlers
│   └── dashboard.css       # Clean SaaS dashboard styling
├── utils/
│   ├── storage.js          # Persistent Chrome storage manager with midnight reset
│   ├── audio.js            # Synthesized Web Audio chime (no external audio files needed)
│   └── csv.js              # CSV parser, exporter, and Excel error detector
├── samples/
│   ├── keywords.csv        # Sample keywords CSV template
│   ├── locations.csv       # Sample domestic locations CSV
│   ├── export_countries.csv# Sample export countries CSV
│   └── negative_keywords.csv# Sample negative keywords list
├── icons/                  # High-res extension icons (16px, 48px, 128px)
└── test-leadlist.html      # Local mock BuyLeads page for instant testing
```

---

## 📄 CSV File Formats

### 1. Keyword CSV
Save as **CSV UTF-8 (Comma delimited)**:
```csv
keyword,qty,unit,category,clicks,min_order_value,target_location
Electric Stacker,1,Piece,Material Handling,0,0,Maharashtra
Scissor Lift,1,Piece,Industrial Machinery,0,0,
Electric Forklift,1,Piece,Warehouse Equipment,0,75000,Gujarat
```

### 2. Location CSV
```csv
location
Maharashtra
Gujarat
Delhi
Karnataka
```

### 3. Export Country CSV
```csv
country
United States
United Kingdom
United Arab Emirates
Germany
```

---

## 🧪 Testing the Extension

1. Click on the extension icon in your browser toolbar or click **"Open Advanced Rules Dashboard"**.
2. Click on the **"🧪 Lead Simulator"** tab.
3. Click **"Load Preset Example"** and click **"⚡ Test Against My Rules"**.
4. You will see an instant evaluation explaining why the lead is matched or rejected based on your active rules.
5. To test in an actual webpage DOM, open `test-leadlist.html` in your browser.

