"""
Aguatech Engineers Pvt. Ltd. - Web Command Dashboard & Asset Master
Interactive Management Portal for Category-City Priority, Buyer Authentication Filters,
Live IndiaMART Lead Intelligence Stream, and Monthly/Daily Quota Controls.

Access: http://localhost:8501 or http://100.103.78.21:8501 via Tailscale
"""

import http.server
import json
import logging
import os
import socketserver
import subprocess
import sys
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List

# Configure Windows console for UTF-8 compatibility
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AguatechBot.Dashboard")

PORT = int(os.getenv("DASHBOARD_PORT", "8501"))
CONFIG_FILE = "config.json"
HISTORY_FILE = "leads_history.json"


def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {CONFIG_FILE}: {e}")
    return {}


def save_config(data: Dict[str, Any]) -> bool:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {CONFIG_FILE}: {e}")
        return False


def load_history() -> List[Dict[str, Any]]:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Aguatech Engineers - IndiaMART Auto-Buy Master</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #080b11;
      --card-bg: rgba(16, 23, 38, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover-border: rgba(99, 102, 241, 0.45);
      --primary: #4f46e5;
      --primary-hover: #4338ca;
      --accent-cyan: #06b6d4;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #f43f5e;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-sub: #64748b;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-dark);
      background-image: 
        radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.18) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.12) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
      background-attachment: fixed;
      color: var(--text-main);
      min-height: 100vh;
      line-height: 1.5;
    }

    .container { max-width: 1440px; margin: 0 auto; padding: 24px; }

    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      background: var(--card-bg);
      backdrop-filter: blur(20px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      margin-bottom: 24px;
    }

    .brand { display: flex; align-items: center; gap: 16px; }
    .brand-logo {
      width: 46px; height: 46px; border-radius: 12px;
      background: linear-gradient(135deg, #4f46e5, #06b6d4);
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 22px;
      box-shadow: 0 4px 20px rgba(79, 70, 229, 0.4);
    }
    .brand-title h1 { font-size: 1.2rem; font-weight: 700; letter-spacing: -0.02em; }
    .brand-title p { font-size: 0.8rem; color: var(--text-muted); }

    .header-actions { display: flex; align-items: center; gap: 14px; }
    .badge {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 6px 14px; border-radius: 20px; font-size: 0.78rem; font-weight: 600;
      border: 1px solid transparent;
    }
    .badge-dot { width: 8px; height: 8px; border-radius: 50%; animation: pulse 2s infinite; }
    .badge-live { background: rgba(16, 185, 129, 0.15); color: #34d399; border-color: rgba(16, 185, 129, 0.3); }
    .badge-live .badge-dot { background: #34d399; }
    .badge-dryrun { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.3); }
    .badge-dryrun .badge-dot { background: #fbbf24; }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.9); }
    }

    /* KPI Grid */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 18px; margin-bottom: 24px;
    }
    .kpi-card {
      background: var(--card-bg); backdrop-filter: blur(16px);
      border: 1px solid var(--card-border); border-radius: 16px; padding: 20px;
      transition: all 0.2s ease;
    }
    .kpi-card:hover { border-color: var(--card-hover-border); transform: translateY(-2px); }
    .kpi-label { font-size: 0.8rem; color: var(--text-muted); font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.04em; }
    .kpi-val { font-size: 1.85rem; font-weight: 800; color: var(--text-main); }
    .kpi-sub { font-size: 0.75rem; color: var(--text-sub); margin-top: 4px; }

    /* Navigation Tabs */
    .tabs-nav {
      display: flex; gap: 8px; background: rgba(15, 23, 42, 0.6);
      padding: 6px; border-radius: 14px; border: 1px solid var(--card-border);
      margin-bottom: 24px;
    }
    .tab-btn {
      flex: 1; padding: 12px 18px; background: transparent; border: none;
      color: var(--text-muted); font-size: 0.9rem; font-weight: 600;
      border-radius: 10px; cursor: pointer; transition: all 0.2s ease;
      display: flex; align-items: center; justify-content: center; gap: 8px;
    }
    .tab-btn:hover { color: var(--text-main); background: rgba(255, 255, 255, 0.04); }
    .tab-btn.active { background: var(--primary); color: #fff; box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4); }

    .tab-pane { display: none; }
    .tab-pane.active { display: block; }

    /* Cards & Containers */
    .panel-card {
      background: var(--card-bg); backdrop-filter: blur(16px);
      border: 1px solid var(--card-border); border-radius: 16px;
      padding: 24px; margin-bottom: 24px;
    }
    .panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .panel-header h2 { font-size: 1.15rem; font-weight: 700; }
    .panel-header p { font-size: 0.8rem; color: var(--text-muted); }

    /* Buttons */
    .btn {
      padding: 10px 20px; border-radius: 10px; font-size: 0.85rem; font-weight: 600;
      cursor: pointer; transition: all 0.2s ease; border: 1px solid transparent;
      display: inline-flex; align-items: center; gap: 8px;
    }
    .btn-primary { background: var(--primary); color: #fff; }
    .btn-primary:hover { background: var(--primary-hover); transform: translateY(-1px); }
    .btn-secondary { background: rgba(255, 255, 255, 0.06); color: var(--text-main); border-color: var(--card-border); }
    .btn-secondary:hover { background: rgba(255, 255, 255, 0.1); }
    .btn-danger { background: rgba(244, 63, 94, 0.15); color: #fb7185; border-color: rgba(244, 63, 94, 0.3); }

    /* Table */
    .custom-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .custom-table th { text-align: left; padding: 12px 16px; background: rgba(0, 0, 0, 0.25); color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.72rem; letter-spacing: 0.05em; }
    .custom-table td { padding: 14px 16px; border-bottom: 1px solid var(--card-border); }
    .custom-table tr:hover { background: rgba(255, 255, 255, 0.02); }

    /* Select, Inputs */
    select, input[type="text"], input[type="number"], textarea {
      background: rgba(10, 15, 26, 0.8); border: 1px solid var(--card-border);
      border-radius: 8px; color: var(--text-main); padding: 8px 12px; font-size: 0.85rem;
      outline: none; transition: border 0.2s;
    }
    select:focus, input:focus, textarea:focus { border-color: var(--primary); }

    .tier-select { font-weight: 600; padding: 6px 10px; }
    .tier-1 { color: #34d399; }
    .tier-2 { color: #38bdf8; }
    .tier-3 { color: #fbbf24; }

    /* Tags */
    .city-tags { display: flex; flex-wrap: wrap; gap: 6px; }
    .tag { background: rgba(255, 255, 255, 0.06); padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; color: var(--text-muted); }

    /* Lead Feed Card */
    .lead-card {
      background: rgba(10, 15, 26, 0.5); border: 1px solid var(--card-border);
      border-radius: 12px; padding: 18px; margin-bottom: 14px;
      transition: all 0.2s ease;
    }
    .lead-card:hover { border-color: var(--card-hover-border); transform: translateX(4px); }
    .lead-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
    .lead-title { font-size: 1rem; font-weight: 700; color: #fff; }
    .lead-meta { display: flex; gap: 14px; font-size: 0.78rem; color: var(--text-muted); margin-bottom: 10px; }
    .buyer-box {
      background: rgba(0, 0, 0, 0.3); border-radius: 8px; padding: 10px 14px;
      display: flex; justify-content: space-between; align-items: center; margin-top: 10px;
      font-size: 0.8rem;
    }
    .buyer-metrics { display: flex; gap: 12px; color: var(--text-muted); }
    .metric-badge { padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.72rem; }
    .metric-gst { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .metric-mob { background: rgba(6, 182, 212, 0.2); color: #22d3ee; }
    .metric-wa { background: rgba(37, 211, 102, 0.2); color: #25d366; }

    /* Toggle Switch */
    .switch { position: relative; display: inline-block; width: 48px; height: 26px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #334155; transition: .3s; border-radius: 26px; }
    .slider:before { position: absolute; content: ""; height: 20px; width: 20px; left: 3px; bottom: 3px; background-color: white; transition: .3s; border-radius: 50%; }
    input:checked + .slider { background-color: var(--accent-emerald); }
    input:checked + .slider:before { transform: translateX(22px); }

    .toast {
      position: fixed; bottom: 24px; right: 24px; padding: 14px 24px; border-radius: 10px;
      background: #10b981; color: #fff; font-weight: 600; font-size: 0.85rem;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4); display: none; z-index: 9999;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-logo">A</div>
        <div class="brand-title">
          <h1>Aguatech Engineers Pvt. Ltd.</h1>
          <p>IndiaMART BuyLead Sniper & Asset Master</p>
        </div>
      </div>
      <div class="header-actions">
        <span id="mode-badge" class="badge badge-dryrun">
          <span class="badge-dot"></span>
          <span id="mode-text">DRY-RUN MODE</span>
        </span>
        <button class="btn btn-secondary" onclick="sendTestAlert()">🔔 Ping Telegram</button>
        <button class="btn btn-primary" onclick="saveAllSettings()">💾 Save Changes</button>
      </div>
    </header>

    <!-- Top KPI Grid -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Today's Consumption</div>
        <div class="kpi-val" id="kpi-today">0 / 11</div>
        <div class="kpi-sub">Target: 11 leads/day (3 Bonus + 8 Paid)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Weekly Quota</div>
        <div class="kpi-val" id="kpi-week">0 / 70</div>
        <div class="kpi-sub">Resets every Monday morning</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Monthly Remaining</div>
        <div class="kpi-val" id="kpi-month">100 Leads</div>
        <div class="kpi-sub">Billing Cycle Resets on 7th of Every Month</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Gateway Network</div>
        <div class="kpi-val" style="color: #34d399; font-size: 1.3rem; margin-top: 6px;">● Online (Direct Jio)</div>
        <div class="kpi-sub">Failover: PC (Day) + Mobile (Night)</div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs-nav">
      <button class="tab-btn active" onclick="switchTab('tab-categories')">📦 Category & City Matrix</button>
      <button class="tab-btn" onclick="switchTab('tab-buyer')">🛡️ Buyer Quality & Filters</button>
      <button class="tab-btn" onclick="switchTab('tab-quota')">📊 Quota & Live Controls</button>
      <button class="tab-btn" onclick="switchTab('tab-leads')">📡 Live Lead Stream</button>
    </div>

    <!-- TAB 1: Category & City Matrix -->
    <div id="tab-categories" class="tab-pane active">
      <div class="panel-card">
        <div class="panel-header">
          <div>
            <h2>IndiaMART Category & City Priority Setup</h2>
            <p>Mapped directly to Aguatech's Leader Value+ categories and consumption history.</p>
          </div>
          <button class="btn btn-primary" onclick="saveAllSettings()">Save Matrix</button>
        </div>
        <table class="custom-table" id="matrix-table">
          <thead>
            <tr>
              <th>Category Name</th>
              <th>Priority Tier</th>
              <th>City Coverage Scope</th>
              <th>Action Mode</th>
            </tr>
          </thead>
          <tbody id="matrix-tbody">
            <!-- Dynamically populated via JS -->
          </tbody>
        </table>
      </div>
    </div>

    <!-- TAB 2: Buyer Quality & Filters -->
    <div id="tab-buyer" class="tab-pane">
      <div class="panel-card">
        <div class="panel-header">
          <div>
            <h2>Buyer Authentication & Quality Gates</h2>
            <p>Prevent wasting credits on unverified, casual, or non-responsive inquiries.</p>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
          <div>
            <div style="margin-bottom: 20px;">
              <label style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 600;">Require Mobile Verified Buyer</span>
                <label class="switch">
                  <input type="checkbox" id="require_mobile_verified">
                  <span class="slider"></span>
                </label>
              </label>
              <p style="font-size: 0.78rem; color: var(--text-muted);">Skips leads where the buyer's phone number has not been validated by IndiaMART.</p>
            </div>

            <div style="margin-bottom: 20px;">
              <label style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 600;">Require GST Registered Business</span>
                <label class="switch">
                  <input type="checkbox" id="require_gst_buyer">
                  <span class="slider"></span>
                </label>
              </label>
              <p style="font-size: 0.78rem; color: var(--text-muted);">Only purchases leads from buyers with an active GSTIN number.</p>
            </div>

            <div style="margin-bottom: 20px;">
              <label style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 600;">Pan-India Auto-Buy for Tier 1 (Goods Lifts & Forklifts)</span>
                <label class="switch">
                  <input type="checkbox" id="pan_india_for_tier1">
                  <span class="slider"></span>
                </label>
              </label>
              <p style="font-size: 0.78rem; color: var(--text-muted);">Allows high-value capital equipment leads to be purchased across all Indian states.</p>
            </div>
          </div>

          <div>
            <div style="margin-bottom: 20px;">
              <label style="display: block; font-weight: 600; margin-bottom: 6px;">Minimum Order Quantity</label>
              <input type="number" id="min_order_quantity" min="1" max="100" style="width: 100%;">
              <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">Ignore hobbyist inquiries under this piece quantity.</p>
            </div>

            <div style="margin-bottom: 20px;">
              <label style="display: block; font-weight: 600; margin-bottom: 6px;">Negative / Excluded Keywords (Strict Block)</label>
              <textarea id="excluded_keywords" rows="4" style="width: 100%; font-family: monospace;"></textarea>
              <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">Comma-separated terms that will immediately reject the lead (e.g. used, rent, repair, scrap, toy).</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: Quota & Live Controls -->
    <div id="tab-quota" class="tab-pane">
      <div class="panel-card">
        <div class="panel-header">
          <div>
            <h2>Quota & Scheduling Controls</h2>
            <p>Ensure your 300 monthly credits + 3 daily bonus leads are perfectly utilized without overspending.</p>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 24px;">
          <div style="background: rgba(0,0,0,0.3); padding: 18px; border-radius: 12px; border: 1px solid var(--card-border);">
            <label style="display: block; font-weight: 600; margin-bottom: 6px;">Daily Lead Cap</label>
            <input type="number" id="max_leads_per_day" style="width: 100%;">
            <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">Recommended: 11 leads/day (Fully exhausts 330 leads/month).</p>
          </div>
          <div style="background: rgba(0,0,0,0.3); padding: 18px; border-radius: 12px; border: 1px solid var(--card-border);">
            <label style="display: block; font-weight: 600; margin-bottom: 6px;">Weekly Lead Cap</label>
            <input type="number" id="max_leads_per_week" style="width: 100%;">
            <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">Default: 70 leads/week.</p>
          </div>
          <div style="background: rgba(0,0,0,0.3); padding: 18px; border-radius: 12px; border: 1px solid var(--card-border);">
            <label style="display: block; font-weight: 600; margin-bottom: 6px;">Monthly Quota Reset Day</label>
            <input type="number" id="quota_reset_day_of_month" style="width: 100%;">
            <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">IndiaMART billing reset date (Set to 7th).</p>
          </div>
        </div>

        <div style="background: rgba(79, 70, 229, 0.1); border: 1px solid rgba(79, 70, 229, 0.3); border-radius: 14px; padding: 20px; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h3 style="font-size: 1.05rem; margin-bottom: 4px;">🚀 Live Credit Spending Switch</h3>
            <p style="font-size: 0.8rem; color: var(--text-muted);">When turned ON, the sniper bot consumes real IndiaMART credits for matched Tier 1 & 2 leads.</p>
          </div>
          <label class="switch">
            <input type="checkbox" id="master_live_switch" onchange="toggleLiveMode(this.checked)">
            <span class="slider"></span>
          </label>
        </div>
      </div>
    </div>

    <!-- TAB 4: Live Lead Stream -->
    <div id="tab-leads" class="tab-pane">
      <div class="panel-card">
        <div class="panel-header">
          <div>
            <h2>Live Capture & CRM Activity Stream</h2>
            <p>Real-time buyer activity, responsiveness ratings, and transactional audit trail.</p>
          </div>
          <button class="btn btn-secondary" onclick="fetchLeadsHistory()">🔄 Refresh Stream</button>
        </div>
        <div id="leads-container">
          <p style="color: var(--text-muted); font-size: 0.85rem;">Loading lead pipeline history...</p>
        </div>
      </div>
    </div>
  </div>

  <div id="toast" class="toast">Settings Saved Successfully!</div>

  <script>
    let globalConfig = {};

    const CATEGORY_CATALOG = [
      { name: "Goods Lift", key: "goods lift", defaultTier: 1, cities: ["Pune", "Mumbai", "Vadodara", "Chennai", "Ankleshwar", "Kolhapur", "Nagpur", "Nashik", "Hyderabad", "Bengaluru"] },
      { name: "Hydraulic Scissor Lift", key: "hydraulic scissor lift", defaultTier: 1, cities: ["Pune", "Mumbai", "Bengaluru", "Chhatrapati Sambhajinagar", "Navi Mumbai", "Thane", "Pimpri Chinchwad"] },
      { name: "Scissor Lift Tables", key: "scissor lift tables", defaultTier: 1, cities: ["Pune", "Mumbai", "Nashik", "Navi Mumbai", "Ahilyanagar"] },
      { name: "Self Propelled Scissor Lift", key: "self propelled scissor lift", defaultTier: 1, cities: ["Pune", "Hyderabad", "Mumbai", "Thane", "Bengaluru", "Nagpur", "Chennai"] },
      { name: "Electric Forklift & Trucks", key: "electric forklift", defaultTier: 1, cities: ["Vadodara", "Bengaluru", "Pune", "Thane", "Chennai", "Mumbai"] },
      { name: "Electric Stacker & Reach Stacker", key: "electric stacker", defaultTier: 1, cities: ["Pune", "Nashik", "Mumbai", "Nagpur", "Thane", "Hyderabad", "Mysore", "Ankleshwar", "Chennai"] },
      { name: "Hydraulic Floor Cranes", key: "hydraulic floor cranes", defaultTier: 1, cities: ["Pune", "Mumbai", "Bengaluru", "Hyderabad", "Chhatrapati Sambhajinagar", "Kolhapur", "Nashik"] },
      { name: "Battery Operated Pallet Truck (BOPT)", key: "battery operated pallet truck", defaultTier: 2, cities: ["Mumbai", "Ahmedabad", "Gurugram", "Pune", "Thane", "Chennai"] },
      { name: "Hand Pallet Truck & Jacks", key: "hand pallet truck", defaultTier: 2, cities: ["Pune", "Mumbai", "Bengaluru", "Kolhapur", "Pimpri Chinchwad", "Ahmedabad", "Nagpur"] },
      { name: "Manual Stacker", key: "manual stacker", defaultTier: 2, cities: ["Pune", "Mumbai", "Thane", "Chhatrapati Sambhajinagar", "Kolhapur", "Nagpur", "Nashik", "Sangli"] },
      { name: "Semi Electric Stacker", key: "semi electric stacker", defaultTier: 2, cities: ["Mumbai", "Nashik", "Pune", "Ahmedabad", "Delhi", "Hyderabad", "Navi Mumbai", "Jaipur"] },
      { name: "Hydraulic Ladder & Aerial Platforms", key: "hydraulic ladder", defaultTier: 2, cities: ["Vijayawada", "Ahmednagar", "Pune", "Chennai", "Coimbatore", "Mumbai", "Hyderabad", "Nagpur"] },
      { name: "Dock Leveler & Loading Ramps", key: "dock leveler", defaultTier: 2, cities: ["Pune", "Mumbai", "Chennai", "Nagpur", "Navi Mumbai", "Thane"] },
      { name: "Drum Lifter, Tilter & Trolley", key: "drum lifter", defaultTier: 3, cities: ["Pune", "Bengaluru", "Mumbai", "Hyderabad", "Ahmedabad"] },
      { name: "Die Loader & Die Tables", key: "die loader", defaultTier: 3, cities: ["Pune", "Mumbai", "Ahmedabad"] }
    ];

    async function initDashboard() {
      try {
        const res = await fetch('/api/get_config');
        globalConfig = await res.json();
        populateForm(globalConfig);
        renderCategoryMatrix(globalConfig);
        fetchLeadsHistory();
      } catch (err) {
        console.error("Failed to load config:", err);
      }
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      event.currentTarget.classList.add('active');
    }

    function populateForm(cfg) {
      const filters = cfg.filters || {};
      const sys = cfg.system_settings || {};

      document.getElementById('require_mobile_verified').checked = !!filters.require_mobile_verified;
      document.getElementById('require_gst_buyer').checked = !!filters.require_gst_buyer;
      document.getElementById('pan_india_for_tier1').checked = filters.pan_india_for_tier1 !== false;
      document.getElementById('min_order_quantity').value = filters.min_order_quantity || 1;
      document.getElementById('excluded_keywords').value = (filters.excluded_keywords || []).join(', ');

      document.getElementById('max_leads_per_day').value = sys.max_leads_per_day || 11;
      document.getElementById('max_leads_per_week').value = sys.max_leads_per_week || 70;
      document.getElementById('quota_reset_day_of_month').value = sys.quota_reset_day_of_month || 7;

      const isLive = sys.dry_run_mode === false;
      document.getElementById('master_live_switch').checked = isLive;
      updateLiveBadge(isLive);
    }

    function updateLiveBadge(isLive) {
      const b = document.getElementById('mode-badge');
      const t = document.getElementById('mode-text');
      if (isLive) {
        b.className = "badge badge-live";
        t.innerText = "🚀 LIVE PURCHASING (CREDITS ACTIVE)";
      } else {
        b.className = "badge badge-dryrun";
        t.innerText = "🟡 DRY-RUN (SIMULATION)";
      }
    }

    function renderCategoryMatrix(cfg) {
      const tbody = document.getElementById('matrix-tbody');
      tbody.innerHTML = '';

      const pTiers = cfg.filters?.priority_tiers || {};
      const t1 = pTiers.tier_1_high_priority_buy || [];
      const t2 = pTiers.tier_2_standard_buy || [];
      const t3 = pTiers.tier_3_alert_only || [];

      CATEGORY_CATALOG.forEach(item => {
        let currentTier = item.defaultTier;
        if (t1.some(k => k.toLowerCase() === item.key.toLowerCase())) currentTier = 1;
        else if (t2.some(k => k.toLowerCase() === item.key.toLowerCase())) currentTier = 2;
        else if (t3.some(k => k.toLowerCase() === item.key.toLowerCase())) currentTier = 3;

        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong style="color: #fff;">${item.name}</strong><br><span style="font-size: 0.72rem; color: var(--text-sub);">${item.key}</span></td>
          <td>
            <select class="tier-select tier-${currentTier}" data-key="${item.key}" onchange="this.className='tier-select tier-' + this.value">
              <option value="1" class="tier-1" ${currentTier === 1 ? 'selected' : ''}>🟢 Tier 1 (High Priority Auto-Buy)</option>
              <option value="2" class="tier-2" ${currentTier === 2 ? 'selected' : ''}>🔵 Tier 2 (Standard Auto-Buy)</option>
              <option value="3" class="tier-3" ${currentTier === 3 ? 'selected' : ''}>🟡 Tier 3 (Alert Only - 0 Credits)</option>
              <option value="0" ${currentTier === 0 ? 'selected' : ''}>🔴 Disabled / Excluded</option>
            </select>
          </td>
          <td>
            <div class="city-tags">
              ${item.cities.slice(0, 5).map(c => `<span class="tag">${c}</span>`).join('')}
              ${item.cities.length > 5 ? `<span class="tag">+${item.cities.length - 5} more</span>` : ''}
            </div>
          </td>
          <td>
            <span style="font-size: 0.75rem; font-weight: 600; color: ${currentTier === 1 ? '#34d399' : (currentTier === 2 ? '#38bdf8' : '#fbbf24')};">
              ${currentTier === 1 ? '⚡ Instant Sniper' : (currentTier === 2 ? '🛒 Daily Quota' : '🔔 Manual Alert')}
            </span>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    async function toggleLiveMode(isLive) {
      updateLiveBadge(isLive);
      globalConfig.system_settings = globalConfig.system_settings || {};
      globalConfig.system_settings.dry_run_mode = !isLive;
      await saveConfigData(globalConfig);
      showToast(isLive ? "🚀 Bot is now LIVE! Purchasing enabled." : "🟡 Bot set to DRY-RUN simulation mode.");
    }

    async function saveAllSettings() {
      // Collect Matrix Selections
      const selects = document.querySelectorAll('.tier-select');
      const t1 = [], t2 = [], t3 = [];

      selects.forEach(s => {
        const key = s.getAttribute('data-key');
        const val = parseInt(s.value);
        if (val === 1) t1.push(key);
        else if (val === 2) t2.push(key);
        else if (val === 3) t3.push(key);
      });

      globalConfig.filters = globalConfig.filters || {};
      globalConfig.filters.priority_tiers = {
        tier_1_high_priority_buy: t1,
        tier_2_standard_buy: t2,
        tier_3_alert_only: t3
      };

      globalConfig.filters.require_mobile_verified = document.getElementById('require_mobile_verified').checked;
      globalConfig.filters.require_gst_buyer = document.getElementById('require_gst_buyer').checked;
      globalConfig.filters.pan_india_for_tier1 = document.getElementById('pan_india_for_tier1').checked;
      globalConfig.filters.min_order_quantity = parseInt(document.getElementById('min_order_quantity').value) || 1;
      globalConfig.filters.excluded_keywords = document.getElementById('excluded_keywords').value.split(',').map(s => s.strip()).filter(Boolean);

      globalConfig.system_settings = globalConfig.system_settings || {};
      globalConfig.system_settings.max_leads_per_day = parseInt(document.getElementById('max_leads_per_day').value) || 11;
      globalConfig.system_settings.max_leads_per_week = parseInt(document.getElementById('max_leads_per_week').value) || 70;
      globalConfig.system_settings.quota_reset_day_of_month = parseInt(document.getElementById('quota_reset_day_of_month').value) || 7;

      await saveConfigData(globalConfig);
      showToast("💾 All Settings & Priorities Saved!");
    }

    async function saveConfigData(cfg) {
      await fetch('/api/save_config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg)
      });
    }

    async function fetchLeadsHistory() {
      try {
        const res = await fetch('/api/get_leads');
        const leads = await res.json();
        const container = document.getElementById('leads-container');
        if (!leads || leads.length === 0) {
          container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No leads captured in current cycle yet. Daemon is monitoring...</p>`;
          return;
        }

        container.innerHTML = leads.slice().reverse().map(l => {
          const m = l.buyer_metrics || {};
          const isGst = m.is_gst ? `<span class="metric-badge metric-gst">🏛️ GST Verified</span>` : '';
          const isMob = m.is_mob ? `<span class="metric-badge metric-mob">📱 Mobile Verified</span>` : '';
          const isWa = m.is_whatsapp ? `<span class="metric-badge metric-wa">💬 WhatsApp</span>` : '';
          const replyStr = m.reply_rate !== undefined ? `${m.reply_rate}% Response Rate (${m.reply_count}/${m.req_count} replies)` : 'Standard Activity';

          return `
            <div class="lead-card">
              <div class="lead-top">
                <div class="lead-title">${l.subject}</div>
                <span class="badge ${l.status.includes('PURCHASED') ? 'badge-live' : 'badge-dryrun'}">${l.status}</span>
              </div>
              <div class="lead-meta">
                <span>📍 ${l.location}</span>
                <span>📊 Qty: ${l.qty}</span>
                <span>🏷️ Matched: <code>${l.matched_keyword || 'MHE'}</code> (Tier ${l.tier || 1})</span>
                <span>⏰ ${new Date(l.timestamp).toLocaleTimeString()}</span>
              </div>
              <div class="buyer-box">
                <div class="buyer-metrics">
                  <span>👤 Member since: <strong>${m.member_since || 'N/A'}</strong></span>
                  <span>📈 ${replyStr}</span>
                </div>
                <div style="display: flex; gap: 6px;">
                  ${isGst} ${isMob} ${isWa}
                </div>
              </div>
            </div>
          `;
        }).join('');
      } catch (e) {
        console.error(e);
      }
    }

    async function sendTestAlert() {
      showToast("Sending test Telegram ping...");
      const res = await fetch('/api/test_telegram');
      const d = await res.json();
      if (d.success) showToast("✅ Telegram Alert Delivered!");
      else alert("Telegram Error: " + d.error);
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.style.display = 'block';
      setTimeout(() => { t.style.display = 'none'; }, 3000);
    }

    window.onload = initDashboard;
  </script>
</body>
</html>
"""


class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        elif parsed.path == "/api/get_config":
            cfg = load_config()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(cfg).encode("utf-8"))

        elif parsed.path == "/api/get_leads":
            history = load_history()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(history).encode("utf-8"))

        elif parsed.path == "/api/test_telegram":
            cfg = load_config()
            token = cfg.get("notifications", {}).get("telegram_bot_token")
            chat_id = cfg.get("notifications", {}).get("telegram_chat_id")
            if not token or not chat_id:
                resp = {"success": False, "error": "Telegram Bot Token or Chat ID is empty."}
            else:
                try:
                    import asyncio
                    from tele_alerts import TelegramNotifier
                    notifier = TelegramNotifier(bot_token=token, chat_id=chat_id)
                    test_lead = {
                        "id": "DIAG-TEST-001",
                        "subject": "Hydraulic Hand Pallet Truck 2.5 Ton (Dashboard Diagnostic)",
                        "location": "Pune, Maharashtra",
                        "qty": 2,
                        "desc": "System ping from Aguatech Dashboard to verify active Telegram alert connectivity.",
                        "buyer_metrics": {
                            "member_since": "10+ years",
                            "is_gst": True,
                            "is_mob": True,
                            "is_whatsapp": True,
                            "req_count": 14,
                            "call_count": 14,
                            "reply_count": 8,
                            "reply_rate": 57.1
                        }
                    }
                    asyncio.run(notifier.send_alert(test_lead, is_dry_run=True, matched_kw="pallet truck", tier=1, quota_str="1/11 today"))
                    resp = {"success": True}
                except Exception as e:
                    resp = {"success": False, "error": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/save_config":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                save_config(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"success": true}')
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_dashboard():
    print("\n" + "=" * 65)
    print("  AGUATECH ENGINEERS - WEB COMMAND PORTAL")
    print("=" * 65)
    print(f"Server URL:     http://localhost:{PORT}")
    print(f"Tailscale URL:  http://100.103.78.21:{PORT}")
    print("=" * 65 + "\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard stopped.")


if __name__ == "__main__":
    run_dashboard()
