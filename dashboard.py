"""
Aguatech Engineers Pvt. Ltd. - Web Command Dashboard & Asset Master
Standalone local portal for Lead CRM, MHE Keyword Management, and System Controls.
Run with: python dashboard.py
"""

import http.server
import json
import logging
import os
import socketserver
import sys
import urllib.parse
from datetime import datetime
from typing import Any, Dict

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


def load_history() -> list:
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
  <title>Aguatech Engineers - IndiaMART Auto-Buy Portal</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0a0d14;
      --card-bg: rgba(18, 24, 38, 0.7);
      --card-border: rgba(255, 255, 255, 0.08);
      --card-hover-border: rgba(99, 102, 241, 0.4);
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

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-dark);
      background-image: 
        radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.15) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.1) 0px, transparent 50%),
        radial-gradient(at 50% 100%, rgba(16, 185, 129, 0.08) 0px, transparent 50%);
      background-attachment: fixed;
      color: var(--text-main);
      min-height: 100vh;
      line-height: 1.5;
    }

    .container {
      max-width: 1400px;
      margin: 0 auto;
      padding: 24px;
    }

    /* Top Navigation Header */
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 24px;
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      margin-bottom: 24px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .brand-logo {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      background: linear-gradient(135deg, #4f46e5, #06b6d4);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 20px;
      box-shadow: 0 4px 16px rgba(79, 70, 229, 0.4);
    }

    .brand-title h1 {
      font-size: 1.15rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }

    .brand-title p {
      font-size: 0.8rem;
      color: var(--text-muted);
    }

    .system-badges {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 600;
      border: 1px solid transparent;
    }

    .badge-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      animation: pulse 2s infinite;
    }

    .badge-dryrun {
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border-color: rgba(245, 158, 11, 0.3);
    }
    .badge-dryrun .badge-dot { background: #fbbf24; }

    .badge-live {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border-color: rgba(16, 185, 129, 0.3);
    }
    .badge-live .badge-dot { background: #34d399; }

    .badge-cookie-ok {
      background: rgba(6, 182, 212, 0.15);
      color: #22d3ee;
      border-color: rgba(6, 182, 212, 0.3);
    }
    .badge-cookie-missing {
      background: rgba(244, 63, 94, 0.15);
      color: #fb7185;
      border-color: rgba(244, 63, 94, 0.3);
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.9); }
    }

    /* KPI Summary Cards */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 20px;
      margin-bottom: 24px;
    }

    .kpi-card {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 20px;
      transition: all 0.2s ease;
    }
    .kpi-card:hover {
      border-color: var(--card-hover-border);
      transform: translateY(-2px);
    }

    .kpi-label {
      font-size: 0.82rem;
      color: var(--text-muted);
      font-weight: 500;
      margin-bottom: 8px;
    }

    .kpi-value {
      font-size: 1.8rem;
      font-weight: 800;
      color: var(--text-main);
      display: flex;
      align-items: baseline;
      gap: 8px;
    }

    .kpi-sub {
      font-size: 0.75rem;
      color: var(--text-sub);
    }

    /* Tabs Navigation */
    .tabs {
      display: flex;
      gap: 8px;
      border-bottom: 1px solid var(--card-border);
      padding-bottom: 12px;
      margin-bottom: 24px;
    }

    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 10px 18px;
      font-size: 0.88rem;
      font-weight: 600;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
      font-family: inherit;
    }

    .tab-btn:hover {
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.05);
    }

    .tab-btn.active {
      color: #fff;
      background: var(--primary);
      box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
    }

    /* Tab Content Sections */
    .tab-content {
      display: none;
    }
    .tab-content.active {
      display: block;
    }

    /* CRM Table */
    .table-card {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      overflow: hidden;
    }

    .table-header {
      padding: 18px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--card-border);
    }

    .table-title {
      font-size: 1.05rem;
      font-weight: 700;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.85rem;
    }

    th {
      padding: 14px 20px;
      color: var(--text-sub);
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.72rem;
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--card-border);
      background: rgba(0, 0, 0, 0.2);
    }

    td {
      padding: 16px 20px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: var(--text-main);
      vertical-align: top;
    }

    tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }

    .lead-tag {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: 6px;
      background: rgba(99, 102, 241, 0.15);
      color: #818cf8;
      border: 1px solid rgba(99, 102, 241, 0.3);
      display: inline-block;
    }

    .lead-status {
      font-size: 0.75rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      display: inline-block;
    }
    .status-dryrun { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
    .status-bought { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .status-rejected { background: rgba(244, 63, 94, 0.15); color: #fb7185; }

    /* Asset Master Layout */
    .chips-container {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 16px;
      background: rgba(0, 0, 0, 0.25);
      border-radius: 12px;
      min-height: 120px;
      max-height: 350px;
      overflow-y: auto;
      border: 1px solid var(--card-border);
      margin-top: 12px;
    }

    .chip {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 0.8rem;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .chip-pos { border-color: rgba(99, 102, 241, 0.3); background: rgba(99, 102, 241, 0.1); }
    .chip-neg { border-color: rgba(244, 63, 94, 0.3); background: rgba(244, 63, 94, 0.1); color: #fca5a5; }
    .chip-loc { border-color: rgba(6, 182, 212, 0.3); background: rgba(6, 182, 212, 0.1); color: #67e8f9; }

    .chip-del {
      cursor: pointer;
      color: var(--text-sub);
      font-weight: bold;
      transition: color 0.2s;
    }
    .chip-del:hover {
      color: var(--accent-rose);
    }

    .input-row {
      display: flex;
      gap: 10px;
      margin-top: 12px;
    }

    input, textarea, select {
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 10px 14px;
      border-radius: 10px;
      font-family: inherit;
      font-size: 0.88rem;
      outline: none;
      transition: border-color 0.2s;
    }
    input:focus, textarea:focus, select:focus {
      border-color: var(--primary);
    }

    .btn {
      background: var(--primary);
      color: white;
      border: none;
      padding: 10px 18px;
      border-radius: 10px;
      font-weight: 600;
      font-size: 0.88rem;
      cursor: pointer;
      transition: all 0.2s ease;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .btn:hover {
      background: var(--primary-hover);
      transform: translateY(-1px);
    }
    .btn-secondary {
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-main);
    }
    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.14);
    }
    .btn-emerald {
      background: var(--accent-emerald);
    }
    .btn-emerald:hover {
      background: #059669;
    }

    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }
    @media (max-width: 900px) {
      .grid-2 { grid-template-columns: 1fr; }
    }

    .form-group {
      margin-bottom: 16px;
    }
    .form-group label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e293b;
      color: #fff;
      padding: 14px 22px;
      border-radius: 12px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
      display: none;
      z-index: 999;
      font-size: 0.88rem;
      font-weight: 500;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="brand">
        <div class="brand-logo">AE</div>
        <div class="brand-title">
          <h1>Aguatech Engineers Pvt. Ltd.</h1>
          <p>Material Handling Equipment (MHE) Lead Autobuy Command Center</p>
        </div>
      </div>
      <div class="system-badges" id="systemBadges">
        <span class="badge badge-dryrun" id="badgeMode">
          <span class="badge-dot"></span> <span id="badgeModeText">Dry-Run Active</span>
        </span>
        <span class="badge badge-cookie-ok" id="badgeCookie">
          Session Cookie Active
        </span>
      </div>
    </header>

    <!-- Top KPI Grid -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">Leads Processed Today</div>
        <div class="kpi-value" id="kpiTodayCount">0 <span class="kpi-sub">/ <span id="kpiMaxCap">15</span> max</span></div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Total Leads in History</div>
        <div class="kpi-value" id="kpiTotalCount">0</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Target MHE Catalog Items</div>
        <div class="kpi-value" id="kpiKeywordCount">87 <span class="kpi-sub">active keywords</span></div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">Sub-Second Polling Speed</div>
        <div class="kpi-value" id="kpiSpeed">0.5s <span class="kpi-sub">ultra high frequency</span></div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('tab-crm')">📋 Lead CRM Feed</button>
      <button class="tab-btn" onclick="switchTab('tab-assets')">🏭 Asset Master (Keywords)</button>
      <button class="tab-btn" onclick="switchTab('tab-settings')">⚙️ Safety & Credentials</button>
      <button class="tab-btn" onclick="switchTab('tab-simulator')">🧪 Simulation & Diagnostics</button>
    </div>

    <!-- TAB 1: Lead CRM Feed -->
    <div id="tab-crm" class="tab-content active">
      <div class="table-card">
        <div class="table-header">
          <div class="table-title">Captured IndiaMART Leads</div>
          <button class="btn btn-secondary" onclick="loadDashboardData()">🔄 Refresh Feed</button>
        </div>
        <div style="overflow-x: auto;">
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Requirement / Product</th>
                <th>Matched Category</th>
                <th>Location</th>
                <th>Qty</th>
                <th>Timestamp</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="leadsTableBody">
              <tr>
                <td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">
                  Loading captured leads...
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 2: Asset Master (Product Range) -->
    <div id="tab-assets" class="tab-content">
      <div class="grid-2">
        <div class="kpi-card">
          <h2 style="font-size: 1.1rem; margin-bottom: 8px;">🎯 Included MHE Product Keywords</h2>
          <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px;">
            The bot matches inquiries containing any of these terms (Pallet trucks, Stackers, Goods lifts, Scissor lifts, etc.)
          </p>
          <div class="input-row">
            <input type="text" id="newKeywordInput" placeholder="e.g. electric reach truck" style="flex: 1;">
            <button class="btn" onclick="addKeyword('included_keywords', 'newKeywordInput')">Add Keyword</button>
          </div>
          <div class="chips-container" id="includedChips"></div>
        </div>

        <div class="kpi-card">
          <h2 style="font-size: 1.1rem; margin-bottom: 8px;">🚫 Excluded Negative Keywords</h2>
          <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px;">
            Any inquiry containing these keywords will be REJECTED instantly to prevent burning credits.
          </p>
          <div class="input-row">
            <input type="text" id="newNegInput" placeholder="e.g. scrap, second hand, toy" style="flex: 1;">
            <button class="btn btn-secondary" onclick="addKeyword('excluded_keywords', 'newNegInput')">Add Excluded</button>
          </div>
          <div class="chips-container" id="excludedChips"></div>
        </div>
      </div>

      <div class="kpi-card" style="margin-top: 20px;">
        <h2 style="font-size: 1.1rem; margin-bottom: 8px;">📍 Target Geographic Clusters</h2>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px;">
          Only inquiries originating from these states and industrial hubs will be purchased.
        </p>
        <div class="input-row">
          <input type="text" id="newLocInput" placeholder="e.g. pune, maharashtra, gujarat" style="flex: 1;">
          <button class="btn btn-secondary" onclick="addKeyword('target_locations', 'newLocInput')">Add Region</button>
        </div>
        <div class="chips-container" id="locationChips"></div>
      </div>
    </div>

    <!-- TAB 3: Safety & Credentials -->
    <div id="tab-settings" class="tab-content">
      <div class="grid-2">
        <div class="kpi-card">
          <h2 style="font-size: 1.1rem; margin-bottom: 16px;">🛡️ Safety & Execution Rules</h2>
          <div class="form-group">
            <label>Operating Mode</label>
            <select id="cfgDryRun" style="width: 100%;">
              <option value="true">🟡 DRY-RUN MODE (Test & Notify Only - Zero Credits Spent)</option>
              <option value="false">🔴 LIVE AUTONOMOUS BUY (Spends Account Credits)</option>
            </select>
          </div>
          <div class="form-group">
            <label>Polling Interval (Seconds)</label>
            <input type="number" step="0.1" id="cfgInterval" style="width: 100%;" value="0.5">
          </div>
          <div class="form-group">
            <label>Max Leads Per Day (Wallet Guard)</label>
            <input type="number" id="cfgMaxLeads" style="width: 100%;" value="15">
          </div>
          <div class="form-group">
            <label>Registered Mobile Number</label>
            <input type="text" id="cfgMobile" style="width: 100%;" placeholder="9876543210">
          </div>
          <button class="btn btn-emerald" onclick="saveSettings()">💾 Save Safety Rules</button>
        </div>

        <div class="kpi-card">
          <h2 style="font-size: 1.1rem; margin-bottom: 16px;">📱 Telegram Notifications & Session</h2>
          <div class="form-group">
            <label>Telegram Bot Token (@BotFather)</label>
            <input type="text" id="cfgTeleToken" style="width: 100%;" placeholder="73829104:AAHj...">
          </div>
          <div class="form-group">
            <label>Telegram Chat ID (Personal or Group)</label>
            <input type="text" id="cfgTeleChat" style="width: 100%;" placeholder="e.g. 987654321 or -100123456789">
          </div>
          <div class="form-group">
            <label>Active IndiaMART Session Cookie</label>
            <textarea id="cfgCookie" rows="3" style="width: 100%; font-family: monospace; font-size: 0.75rem;" placeholder="Paste cookie string extracted from DevTools or session_manager.py"></textarea>
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="btn btn-emerald" onclick="saveSettings()">💾 Save Credentials</button>
            <button class="btn btn-secondary" onclick="triggerTestPing()">📲 Send Test Ping</button>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: Simulation & Diagnostics -->
    <div id="tab-simulator" class="tab-content">
      <div class="kpi-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <div>
            <h2 style="font-size: 1.1rem;">🧪 MHE Filter Diagnostic Suite</h2>
            <p style="font-size: 0.8rem; color: var(--text-muted);">
              Runs 10 realistic marketplace scenarios to verify 100% accuracy of Aguatech catalog matching.
            </p>
          </div>
          <button class="btn btn-emerald" onclick="runSimSuite()">▶️ Execute Test Suite</button>
        </div>
        <div id="simResultsBox" style="background: rgba(0,0,0,0.3); border-radius: 12px; padding: 20px; font-family: monospace; font-size: 0.82rem; white-space: pre-wrap; max-height: 400px; overflow-y: auto;">
Click 'Execute Test Suite' to run diagnostics...
        </div>
      </div>
    </div>
  </div>

  <div class="toast" id="toastBox">Saved successfully</div>

  <script>
    let globalConfig = {};
    let globalHistory = [];

    function showToast(msg) {
      const t = document.getElementById("toastBox");
      t.innerText = msg;
      t.style.display = "block";
      setTimeout(() => { t.style.display = "none"; }, 3000);
    }

    function switchTab(tabId) {
      document.querySelectorAll(".tab-content").forEach(el => el.classList.remove("active"));
      document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));
      document.getElementById(tabId).classList.add("active");
      event.target.classList.add("active");
    }

    async function loadDashboardData() {
      try {
        const res = await fetch("/api/data");
        const data = await res.json();
        globalConfig = data.config;
        globalHistory = data.history;
        renderDashboard();
      } catch (e) {
        console.error("Failed loading data", e);
      }
    }

    function renderDashboard() {
      // Badges
      const isDry = globalConfig.system_settings?.dry_run_mode !== false;
      const bMode = document.getElementById("badgeMode");
      const bModeTxt = document.getElementById("badgeModeText");
      if (isDry) {
        bMode.className = "badge badge-dryrun";
        bModeTxt.innerText = "Dry-Run Active";
      } else {
        bMode.className = "badge badge-live";
        bModeTxt.innerText = "Live Buy Active";
      }

      const hasCookie = !!(globalConfig.indiamart_session?.cookie_string);
      const bCookie = document.getElementById("badgeCookie");
      if (hasCookie) {
        bCookie.className = "badge badge-cookie-ok";
        bCookie.innerText = "Cookie Active";
      } else {
        bCookie.className = "badge badge-cookie-missing";
        bCookie.innerText = "Cookie Missing";
      }

      // KPIs
      document.getElementById("kpiTotalCount").innerText = globalHistory.length;
      document.getElementById("kpiMaxCap").innerText = globalConfig.system_settings?.max_leads_per_day || 15;
      document.getElementById("kpiSpeed").innerText = (globalConfig.system_settings?.polling_interval_seconds || 0.5) + "s";
      document.getElementById("kpiKeywordCount").innerText = (globalConfig.filters?.included_keywords?.length || 0);

      // CRM Table
      const tbody = document.getElementById("leadsTableBody");
      if (!globalHistory || globalHistory.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">No leads captured yet. Run test simulator or activate the engine!</td></tr>`;
      } else {
        tbody.innerHTML = globalHistory.slice().reverse().map(item => {
          let badgeClass = "status-dryrun";
          if (item.status === "PURCHASED") badgeClass = "status-bought";
          else if (item.status?.includes("FAIL") || item.status?.includes("ERROR")) badgeClass = "status-rejected";

          return `
            <tr>
              <td><span class="lead-status ${badgeClass}">${item.status || "DETECTED"}</span></td>
              <td><strong>${escapeHtml(item.subject)}</strong></td>
              <td><span class="lead-tag">${escapeHtml(item.matched_keyword || "MHE")}</span></td>
              <td>${escapeHtml(item.location || "N/A")}</td>
              <td>${escapeHtml(item.qty || 1)}</td>
              <td style="color: var(--text-sub); font-size: 0.78rem;">${(item.timestamp || "").replace("T", " ").substring(0, 19)}</td>
              <td><a href="https://seller.indiamart.com/leadmanager/" target="_blank" class="btn btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;">Open LMS</a></td>
            </tr>
          `;
        }).join("");
      }

      // Chips
      renderChips("includedChips", globalConfig.filters?.included_keywords || [], "chip-pos", "included_keywords");
      renderChips("excludedChips", globalConfig.filters?.excluded_keywords || [], "chip-neg", "excluded_keywords");
      renderChips("locationChips", globalConfig.filters?.target_locations || [], "chip-loc", "target_locations");

      // Settings Inputs
      document.getElementById("cfgDryRun").value = isDry ? "true" : "false";
      document.getElementById("cfgInterval").value = globalConfig.system_settings?.polling_interval_seconds || 0.5;
      document.getElementById("cfgMaxLeads").value = globalConfig.system_settings?.max_leads_per_day || 15;
      document.getElementById("cfgMobile").value = globalConfig.indiamart_session?.account_mobile || "";
      document.getElementById("cfgCookie").value = globalConfig.indiamart_session?.cookie_string || "";
      document.getElementById("cfgTeleToken").value = globalConfig.notifications?.telegram_bot_token || "";
      document.getElementById("cfgTeleChat").value = globalConfig.notifications?.telegram_chat_id || "";
    }

    function renderChips(containerId, list, typeClass, category) {
      const c = document.getElementById(containerId);
      c.innerHTML = list.map((item, idx) => `
        <span class="chip ${typeClass}">
          ${escapeHtml(item)}
          <span class="chip-del" onclick="deleteKeyword('${category}', ${idx})">&times;</span>
        </span>
      `).join("");
    }

    function escapeHtml(str) {
      if (!str) return "";
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    async function addKeyword(category, inputId) {
      const input = document.getElementById(inputId);
      const val = input.value.trim().toLowerCase();
      if (!val) return;
      if (!globalConfig.filters[category]) globalConfig.filters[category] = [];
      if (!globalConfig.filters[category].includes(val)) {
        globalConfig.filters[category].unshift(val);
        input.value = "";
        await postConfig();
        showToast("Added keyword: " + val);
      }
    }

    async function deleteKeyword(category, index) {
      if (globalConfig.filters && globalConfig.filters[category]) {
        globalConfig.filters[category].splice(index, 1);
        await postConfig();
        showToast("Keyword removed");
      }
    }

    async function saveSettings() {
      if (!globalConfig.system_settings) globalConfig.system_settings = {};
      if (!globalConfig.indiamart_session) globalConfig.indiamart_session = {};
      if (!globalConfig.notifications) globalConfig.notifications = {};

      globalConfig.system_settings.dry_run_mode = (document.getElementById("cfgDryRun").value === "true");
      globalConfig.system_settings.polling_interval_seconds = parseFloat(document.getElementById("cfgInterval").value) || 0.5;
      globalConfig.system_settings.max_leads_per_day = parseInt(document.getElementById("cfgMaxLeads").value) || 15;
      globalConfig.indiamart_session.account_mobile = document.getElementById("cfgMobile").value.trim();
      globalConfig.indiamart_session.cookie_string = document.getElementById("cfgCookie").value.trim();
      globalConfig.notifications.telegram_bot_token = document.getElementById("cfgTeleToken").value.trim();
      globalConfig.notifications.telegram_chat_id = document.getElementById("cfgTeleChat").value.trim();

      await postConfig();
      showToast("Configuration saved successfully!");
    }

    async function postConfig() {
      await fetch("/api/save_config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(globalConfig)
      });
      loadDashboardData();
    }

    async function triggerTestPing() {
      showToast("Sending test Telegram alert...");
      const res = await fetch("/api/test_telegram");
      const d = await res.json();
      if (d.success) {
        showToast("Telegram message sent successfully!");
      } else {
        alert("Telegram ping failed. Error: " + (d.error || "Verify token and chat ID"));
      }
    }

    async function runSimSuite() {
      const box = document.getElementById("simResultsBox");
      box.innerText = "Running 10-lead diagnostic simulation...";
      const res = await fetch("/api/run_sim");
      const d = await res.json();
      box.innerText = d.output;
      loadDashboardData();
    }

    window.onload = loadDashboardData;
  </script>
</body>
</html>
"""


class DashboardRequestHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Mute standard noisy HTTP log requests
        return

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        elif parsed.path == "/api/data":
            config = load_config()
            history = load_history()
            payload = json.dumps({"config": config, "history": history})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))

        elif parsed.path == "/api/test_telegram":
            config = load_config()
            token = config.get("notifications", {}).get("telegram_bot_token")
            chat_id = config.get("notifications", {}).get("telegram_chat_id")
            
            if not token or not chat_id:
                resp = {"success": False, "error": "Telegram Bot Token or Chat ID is empty in settings."}
            else:
                try:
                    import httpx
                    import asyncio
                    from tele_alerts import TelegramNotifier
                    notifier = TelegramNotifier(bot_token=token, chat_id=chat_id)
                    test_lead = {
                        "id": "DIAG-TEST-001",
                        "subject": "Hydraulic Hand Pallet Truck 2.5 Ton (Dashboard Diagnostic)",
                        "location": "Pune, Maharashtra",
                        "qty": 2,
                        "desc": "System ping from Aguatech Dashboard to verify active Telegram connectivity."
                    }
                    asyncio.run(notifier.send_alert(test_lead, is_dry_run=True, matched_kw="pallet truck"))
                    resp = {"success": True}
                except Exception as e:
                    resp = {"success": False, "error": str(e)}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        elif parsed.path == "/api/run_sim":
            try:
                import io
                from contextlib import redirect_stdout
                from test_simulator import run_simulation
                import asyncio

                f = io.StringIO()
                with redirect_stdout(f):
                    asyncio.run(run_simulation(send_real_alerts=False))
                output = f.getvalue()
                resp = {"success": True, "output": output}
            except Exception as e:
                resp = {"success": False, "output": f"Simulation execution error: {e}"}

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
    print(f"Asset Master:   Manage MHE keywords & negative filters in browser")
    print(f"Lead CRM:       Real-time pipeline & history viewer")
    print("=" * 65 + "\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), DashboardRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDashboard stopped.")


if __name__ == "__main__":
    run_dashboard()
