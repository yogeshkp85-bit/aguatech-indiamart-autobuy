#!/usr/bin/env python3
"""
Aguatech IndiaMART Mobile & Laptop Web Management Dashboard
Runs on Oracle VM (0.0.0.0:8080).
Accessible via Tailscale from iPhone Safari & Laptop Chrome: http://100.103.78.21:8080
"""

import http.server
import json
import os
import time
import urllib.parse
import subprocess
import threading

PORT = 8080
CONFIG_FILE = "/home/opc/Indiamartgoogleextension/presets/indiamart_autoclick_backup.json"
FALLBACK_CONFIG_FILE = "presets/indiamart_autoclick_backup.json"

def get_config_path():
    if os.path.exists(CONFIG_FILE):
        return CONFIG_FILE
    local = os.path.abspath("Indiamartgoogleextension/presets/indiamart_autoclick_backup.json")
    if os.path.exists(local):
        return local
    return "config.json"

def load_config():
    path = get_config_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "version" not in data:
                data["version"] = 1
            return data
    except Exception as e:
        return {"settings": {}, "keywords": [], "negativeKeywords": [], "locations": [], "blockedLocations": [], "history": [], "stats": {}, "version": 1}

def save_config(data):
    path = get_config_path()
    data["version"] = int(data.get("version", 1)) + 1
    data["lastUpdated"] = int(time.time() * 1000)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Aguatech IndiaMART Lead Manager</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --primary-hover: #2563eb;
      --success: #10b981;
      --danger: #ef4444;
      --warning: #f59e0b;
      --tag-bg: #334155;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', -apple-system, sans-serif; -webkit-tap-highlight-color: transparent; }
    body { background-color: var(--bg); color: var(--text); padding-bottom: 90px; }
    header { background: #1e293b; border-bottom: 1px solid var(--card-border); padding: 16px 20px; position: sticky; top: 0; z-index: 50; display: flex; justify-content: space-between; align-items: center; }
    .brand { display: flex; align-items: center; gap: 10px; }
    .brand-icon { width: 34px; height: 34px; background: linear-gradient(135deg, #3b82f6, #06b6d4); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
    .brand-title { font-size: 17px; font-weight: 700; color: #fff; }
    .brand-subtitle { font-size: 11px; color: var(--text-muted); }
    .badge-status { font-size: 12px; font-weight: 600; padding: 4px 10px; border-radius: 20px; background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); display: flex; align-items: center; gap: 6px; }
    .badge-dot { width: 7px; height: 7px; background: #34d399; border-radius: 50%; animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }

    .nav-tabs { display: flex; background: #1e293b; border-bottom: 1px solid var(--card-border); overflow-x: auto; padding: 0 16px; scrollbar-width: none; }
    .nav-tabs::-webkit-scrollbar { display: none; }
    .nav-tab { padding: 14px 18px; font-size: 14px; font-weight: 600; color: var(--text-muted); border-bottom: 2px solid transparent; cursor: pointer; white-space: nowrap; transition: 0.2s; }
    .nav-tab.active { color: var(--primary); border-bottom-color: var(--primary); }

    .container { max-width: 900px; margin: 0 auto; padding: 20px 16px; }
    .tab-content { display: none; }
    .tab-content.active { display: block; }

    .card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 18px; margin-bottom: 18px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2); }
    .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    .card-title { font-size: 16px; font-weight: 600; color: #fff; }
    .card-desc { font-size: 13px; color: var(--text-muted); margin-top: 2px; }

    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    @media (max-width: 600px) { .grid-2 { grid-template-columns: 1fr; } }

    .form-group { margin-bottom: 14px; }
    label { display: block; font-size: 13px; font-weight: 500; color: var(--text-muted); margin-bottom: 6px; }
    input[type="text"], input[type="number"], select { width: 100%; background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; color: #fff; padding: 10px 12px; font-size: 14px; outline: none; transition: 0.2s; }
    input:focus, select:focus { border-color: var(--primary); }

    .switch-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .switch-row:last-child { border-bottom: none; }
    .switch-label { font-size: 14px; font-weight: 500; color: #f1f5f9; }
    .switch-sub { font-size: 12px; color: var(--text-muted); }

    .switch { position: relative; display: inline-block; width: 44px; height: 24px; flex-shrink: 0; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #475569; transition: .3s; border-radius: 24px; }
    .slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background-color: white; transition: .3s; border-radius: 50%; }
    input:checked + .slider { background-color: var(--primary); }
    input:checked + .slider:before { transform: translateX(20px); }

    .item-row { display: flex; align-items: center; justify-content: space-between; background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; }
    .item-info { flex: 1; }
    .item-title { font-size: 14px; font-weight: 600; color: #fff; }
    .item-meta { font-size: 12px; color: var(--text-muted); margin-top: 3px; }
    .btn-delete { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer; font-weight: 600; }
    .btn-delete:hover { background: var(--danger); color: #fff; }

    .tags-container { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
    .tag { background: var(--tag-bg); border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; padding: 6px 10px; font-size: 13px; color: #e2e8f0; display: flex; align-items: center; gap: 6px; }
    .tag-remove { cursor: pointer; color: #94a3b8; font-size: 14px; font-weight: bold; }
    .tag-remove:hover { color: #f87171; }

    .btn-add { background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.3); color: #60a5fa; border-radius: 8px; padding: 9px 14px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
    .btn-add:hover { background: var(--primary); color: #fff; }

    .bottom-bar { position: fixed; bottom: 0; left: 0; right: 0; background: #1e293b; border-top: 1px solid var(--card-border); padding: 14px 20px; display: flex; justify-content: space-between; align-items: center; z-index: 100; box-shadow: 0 -4px 10px rgba(0,0,0,0.3); }
    .btn-save { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; border: none; border-radius: 8px; padding: 12px 24px; font-size: 15px; font-weight: 600; cursor: pointer; width: 100%; max-width: 300px; margin-left: auto; display: flex; align-items: center; justify-content: center; gap: 8px; box-shadow: 0 4px 12px rgba(37,99,235,0.4); }
    .btn-save:active { transform: scale(0.98); }

    .stat-badge { background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 12px; text-align: center; }
    .stat-num { font-size: 22px; font-weight: 700; color: #fff; }
    .stat-lbl { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

    .toast { position: fixed; bottom: 85px; left: 50%; transform: translateX(-50%); background: #10b981; color: white; padding: 10px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; z-index: 200; box-shadow: 0 4px 12px rgba(0,0,0,0.3); display: none; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="brand-icon">⚡</div>
      <div>
        <div class="brand-title">Aguatech IndiaMART</div>
        <div class="brand-subtitle">Lead Sniper Pro</div>
      </div>
    </div>
    <div class="badge-status" id="gateway-badge">
      <span class="badge-dot"></span>
      <span id="gateway-text">Checking Route...</span>
    </div>
  </header>

  <div class="nav-tabs">
    <div class="nav-tab active" onclick="showTab('keywords')">📦 Products (18)</div>
    <div class="nav-tab" onclick="showTab('locations')">📍 Locations</div>
    <div class="nav-tab" onclick="showTab('negatives')">🚫 Negatives</div>
    <div class="nav-tab" onclick="showTab('settings')">⚙️ Settings</div>
    <div class="nav-tab" onclick="showTab('history')">📊 Leads Today</div>
  </div>

  <div class="container">
    <!-- TAB 1: KEYWORDS -->
    <div id="tab-keywords" class="tab-content active">
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">Add New Product Keyword</div>
            <div class="card-desc">IndiaMART BuyLeads matching this keyword will be evaluated and clicked.</div>
          </div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>Product Keyword Name</label>
            <input type="text" id="new-kw-name" placeholder="e.g. Electric Forklift">
          </div>
          <div class="form-group">
            <label>Minimum Order Qty</label>
            <input type="number" id="new-kw-qty" value="1" min="1">
          </div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>Target Scope</label>
            <select id="new-kw-scope" onchange="toggleScopeInputs()">
              <option value="all">All India (Any Location)</option>
              <option value="global">Global Whitelisted Locations</option>
              <option value="custom">Custom States Selection</option>
            </select>
          </div>
          <div class="form-group" id="custom-states-group" style="display:none;">
            <label>States (Comma separated)</label>
            <input type="text" id="new-kw-states" placeholder="e.g. Maharashtra, Gujarat, Goa">
          </div>
        </div>
        <button class="btn-add" onclick="addKeyword()">➕ Add Product Rule</button>
      </div>

      <div class="card">
        <div class="card-header">
          <div class="card-title">Active Product Keywords (<span id="kw-count">0</span>)</div>
        </div>
        <div id="keyword-list"></div>
      </div>
    </div>

    <!-- TAB 2: LOCATIONS -->
    <div id="tab-locations" class="tab-content">
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">Whitelisted Locations</div>
            <div class="card-desc">Only leads from these states/cities will be captured (unless All-India keyword).</div>
          </div>
        </div>
        <div style="display:flex; gap:10px;">
          <input type="text" id="new-location-input" placeholder="Enter state or city name...">
          <button class="btn-add" onclick="addLocation()">Add</button>
        </div>
        <div class="tags-container" id="locations-tags"></div>
      </div>

      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">Blocked Locations Blacklist</div>
            <div class="card-desc">Leads originating from these regions are immediately rejected.</div>
          </div>
        </div>
        <div style="display:flex; gap:10px;">
          <input type="text" id="new-blocked-location-input" placeholder="Enter state to block...">
          <button class="btn-add" onclick="addBlockedLocation()">Block</button>
        </div>
        <div class="tags-container" id="blocked-locations-tags"></div>
      </div>
    </div>

    <!-- TAB 3: NEGATIVES -->
    <div id="tab-negatives" class="tab-content">
      <div class="card">
        <div class="card-header">
          <div>
            <div class="card-title">Negative Keywords (Banned Terms)</div>
            <div class="card-desc">If lead title contains any of these words, it will NOT be clicked.</div>
          </div>
        </div>
        <div style="display:flex; gap:10px;">
          <input type="text" id="new-neg-input" placeholder="e.g. Scrap, Rental, Repair, Second Hand...">
          <button class="btn-add" onclick="addNegative()">Add Negative</button>
        </div>
        <div class="tags-container" id="negative-tags"></div>
      </div>
    </div>

    <!-- TAB 4: SETTINGS -->
    <div id="tab-settings" class="tab-content">
      <div class="card">
        <div class="card-header">
          <div class="card-title">Automation & Limits</div>
        </div>
        <div class="grid-2">
          <div class="form-group">
            <label>Global Daily Click Limit</label>
            <input type="number" id="setting-limit" value="10">
          </div>
          <div class="form-group">
            <label>Auto-Refresh Interval (Seconds)</label>
            <input type="number" id="setting-interval" value="40" min="15">
          </div>
        </div>
        <div class="switch-row">
          <div>
            <div class="switch-label">Autoclick Engine Active</div>
            <div class="switch-sub">Master switch for autonomous clicking.</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="setting-active" checked>
            <span class="slider"></span>
          </label>
        </div>
        <div class="switch-row">
          <div>
            <div class="switch-label">Require Phone Verified Buyer</div>
            <div class="switch-sub">Only contact leads where buyer mobile number is verified.</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="setting-phone" checked>
            <span class="slider"></span>
          </label>
        </div>
        <div class="switch-row">
          <div>
            <div class="switch-label">Exclude Retail / 1-Piece Leads</div>
            <div class="switch-sub">Ignore inquiries clearly marked as domestic consumer retail.</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="setting-retail">
            <span class="slider"></span>
          </label>
        </div>
      </div>
    </div>

    <!-- TAB 5: HISTORY -->
    <div id="tab-history" class="tab-content">
      <div class="card">
        <div class="card-header">
          <div class="card-title">Today's Click Statistics</div>
        </div>
        <div class="grid-2">
          <div class="stat-badge">
            <div class="stat-num" id="stat-today">0</div>
            <div class="stat-lbl">Clicks Today (Cap: <span id="stat-cap">10</span>)</div>
          </div>
          <div class="stat-badge">
            <div class="stat-num" id="stat-total">0</div>
            <div class="stat-lbl">Lifetime Clicks</div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <div class="card-title">Recent Clicked Leads</div>
        </div>
        <div id="history-list"></div>
      </div>
    </div>
  </div>

  <div class="bottom-bar">
    <div style="font-size:12px; color:var(--text-muted);">
      <div>Auto-syncing with VM Extension</div>
      <div id="sync-status" style="color:#34d399; font-weight:600;">● Online</div>
    </div>
    <button class="btn-save" onclick="saveAll()">💾 Save All Changes</button>
  </div>

  <div class="toast" id="toast">✅ Changes Saved & Synced!</div>

  <script>
    let configData = null;

    function showTab(name) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-tab').forEach(el => el.classList.remove('active'));
      document.getElementById('tab-' + name).classList.add('active');
      event.target.classList.add('active');
    }

    function toggleScopeInputs() {
      const scope = document.getElementById('new-kw-scope').value;
      document.getElementById('custom-states-group').style.display = (scope === 'custom') ? 'block' : 'none';
    }

    async function loadConfig() {
      try {
        const res = await fetch('/api/config');
        configData = await res.json();
        renderAll();
      } catch (e) {
        console.error('Failed to load config:', e);
      }
    }

    async function checkStatus() {
      try {
        const res = await fetch('/api/status');
        const st = await res.json();
        const badge = document.getElementById('gateway-text');
        if (st.gateway === 'PRIMARY_LAPTOP') {
          badge.textContent = 'Active: Office Laptop (' + st.ip + ')';
        } else {
          badge.textContent = 'Active: iPhone 4G/5G (' + st.ip + ')';
        }
      } catch (e) {}
    }

    function renderAll() {
      if (!configData) return;

      // 1. Keywords
      const kwList = document.getElementById('keyword-list');
      kwList.innerHTML = '';
      const kws = configData.keywords || [];
      document.getElementById('kw-count').textContent = kws.length;

      kws.forEach((k, idx) => {
        const row = document.createElement('div');
        row.className = 'item-row';
        let locText = 'Global Rules';
        if (k.targetScope === 'all') locText = 'All India';
        else if (k.targetScope === 'custom' && k.targetStates && k.targetStates.length > 0) {
          locText = k.targetStates.join(', ');
        }
        row.innerHTML = `
          <div class="item-info">
            <div class="item-title">${k.keyword}</div>
            <div class="item-meta">Min Qty: <b>${k.minQty || 1} ${k.unit || 'Piece'}</b> | Scope: <b>${locText}</b></div>
          </div>
          <button class="btn-delete" onclick="removeKeyword(${idx})">Delete</button>
        `;
        kwList.appendChild(row);
      });

      // 2. Locations
      const locContainer = document.getElementById('locations-tags');
      locContainer.innerHTML = '';
      (configData.locations || []).forEach((loc, idx) => {
        const tag = document.createElement('div');
        tag.className = 'tag';
        tag.innerHTML = `${loc} <span class="tag-remove" onclick="removeLocation(${idx})">&times;</span>`;
        locContainer.appendChild(tag);
      });

      // 3. Blocked Locations
      const bLocContainer = document.getElementById('blocked-locations-tags');
      bLocContainer.innerHTML = '';
      (configData.blockedLocations || []).forEach((bloc, idx) => {
        const tag = document.createElement('div');
        tag.className = 'tag';
        tag.style.background = 'rgba(239,68,68,0.2)';
        tag.style.borderColor = 'rgba(239,68,68,0.4)';
        tag.innerHTML = `${bloc} <span class="tag-remove" onclick="removeBlockedLocation(${idx})">&times;</span>`;
        bLocContainer.appendChild(tag);
      });

      // 4. Negatives
      const negContainer = document.getElementById('negative-tags');
      negContainer.innerHTML = '';
      (configData.negativeKeywords || []).forEach((neg, idx) => {
        const tag = document.createElement('div');
        tag.className = 'tag';
        tag.innerHTML = `${neg} <span class="tag-remove" onclick="removeNegative(${idx})">&times;</span>`;
        negContainer.appendChild(tag);
      });

      // 5. Settings
      const s = configData.settings || {};
      document.getElementById('setting-limit').value = s.globalDailyClickLimit || 10;
      document.getElementById('setting-interval').value = s.refreshInterval || 40;
      document.getElementById('setting-active').checked = (s.engineActive !== false);
      document.getElementById('setting-phone').checked = (s.verificationTypes && s.verificationTypes.phone !== false);
      document.getElementById('setting-retail').checked = (s.excludeRetailLeads === true);

      // 6. Stats & History
      const stats = configData.stats || {};
      document.getElementById('stat-today').textContent = stats.clicksToday || 0;
      document.getElementById('stat-cap').textContent = s.globalDailyClickLimit || 10;
      document.getElementById('stat-total').textContent = stats.totalClicks || 0;

      const hList = document.getElementById('history-list');
      hList.innerHTML = '';
      const hist = configData.history || [];
      if (hist.length === 0) {
        hList.innerHTML = '<div style="font-size:13px; color:var(--text-muted); text-align:center; padding:20px;">No leads clicked yet today.</div>';
      } else {
        hist.slice(0, 15).forEach(h => {
          const item = document.createElement('div');
          item.className = 'item-row';
          item.innerHTML = `
            <div class="item-info">
              <div class="item-title">${h.title || 'IndiaMART Lead'}</div>
              <div class="item-meta">Buyer: <b>${(h.buyerLocation || '').replace(/\\n/g, ' ')}</b> | Value: <b>${h.orderValue || 'N/A'}</b> | Time: <b>${h.timeFormatted || 'Today'}</b></div>
            </div>
            <div style="color:#10b981; font-weight:700; font-size:12px;">CLICKED</div>
          `;
          hList.appendChild(item);
        });
      }
    }

    function addKeyword() {
      const name = document.getElementById('new-kw-name').value.trim();
      const qty = parseInt(document.getElementById('new-kw-qty').value) || 1;
      const scope = document.getElementById('new-kw-scope').value;
      const statesRaw = document.getElementById('new-kw-states').value;

      if (!name) return alert('Please enter product keyword name');

      let states = [];
      if (scope === 'custom') {
        states = statesRaw.split(',').map(s => s.trim()).filter(Boolean);
      }

      configData.keywords.push({
        id: 'kw-' + Date.now(),
        keyword: name,
        minQty: qty,
        unit: 'Piece',
        targetScope: scope,
        targetStates: states,
        targetCities: [],
        targetLocation: (scope === 'all') ? 'All India' : states.join(', '),
        clicksToday: 0,
        dailyLimit: 0,
        minOrderValue: 0
      });

      document.getElementById('new-kw-name').value = '';
      document.getElementById('new-kw-states').value = '';
      renderAll();
    }

    function removeKeyword(idx) {
      if (confirm('Delete keyword: ' + configData.keywords[idx].keyword + '?')) {
        configData.keywords.splice(idx, 1);
        renderAll();
      }
    }

    function addLocation() {
      const val = document.getElementById('new-location-input').value.trim();
      if (!val) return;
      if (!configData.locations.includes(val)) {
        configData.locations.push(val);
      }
      document.getElementById('new-location-input').value = '';
      renderAll();
    }

    function removeLocation(idx) {
      configData.locations.splice(idx, 1);
      renderAll();
    }

    function addBlockedLocation() {
      const val = document.getElementById('new-blocked-location-input').value.trim();
      if (!val) return;
      if (!configData.blockedLocations.includes(val)) {
        configData.blockedLocations.push(val);
      }
      document.getElementById('new-blocked-location-input').value = '';
      renderAll();
    }

    function removeBlockedLocation(idx) {
      configData.blockedLocations.splice(idx, 1);
      renderAll();
    }

    function addNegative() {
      const val = document.getElementById('new-neg-input').value.trim();
      if (!val) return;
      if (!configData.negativeKeywords.includes(val)) {
        configData.negativeKeywords.push(val);
      }
      document.getElementById('new-neg-input').value = '';
      renderAll();
    }

    function removeNegative(idx) {
      configData.negativeKeywords.splice(idx, 1);
      renderAll();
    }

    async function saveAll() {
      // Gather settings
      configData.settings.globalDailyClickLimit = parseInt(document.getElementById('setting-limit').value) || 10;
      configData.settings.refreshInterval = parseInt(document.getElementById('setting-interval').value) || 40;
      configData.settings.engineActive = document.getElementById('setting-active').checked;
      if (!configData.settings.verificationTypes) configData.settings.verificationTypes = {};
      configData.settings.verificationTypes.phone = document.getElementById('setting-phone').checked;
      configData.settings.excludeRetailLeads = document.getElementById('setting-retail').checked;

      try {
        const res = await fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(configData)
        });
        const saved = await res.json();
        configData = saved;
        showToast('✅ Saved & Synced with VM Bot!');
        renderAll();
      } catch (e) {
        alert('Error saving config: ' + e);
      }
    }

    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.style.display = 'block';
      setTimeout(() => { t.style.display = 'none'; }, 3000);
    }

    loadConfig();
    checkStatus();
    setInterval(checkStatus, 5000);
  </script>
</body>
</html>
"""

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path in ["", "/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif url.path == "/api/config":
            cfg = load_config()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(cfg).encode("utf-8"))
        elif url.path == "/api/status":
            # Check active gateway
            try:
                res = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True)
                data = json.loads(res.stdout)
                peers = data.get("Peer", {})
                gw = "SECONDARY_IPHONE"
                ip = "152.59.63.105"
                # Check if laptop is pingable / proxy responding
                import socket
                s = socket.socket()
                s.settimeout(1.0)
                try:
                    s.connect(("100.99.64.16", 8888))
                    s.close()
                    gw = "PRIMARY_LAPTOP"
                    ip = "152.58.17.84"
                except:
                    pass
                status_info = {"gateway": gw, "ip": ip}
            except Exception:
                status_info = {"gateway": "PRIMARY_LAPTOP", "ip": "152.58.17.84"}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(status_info).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/config":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body.decode("utf-8"))
                saved = save_config(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(saved).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
        elif url.path == "/api/record_click":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                click_data = json.loads(body.decode("utf-8"))
                cfg = load_config()
                if "history" not in cfg: cfg["history"] = []
                if "stats" not in cfg: cfg["stats"] = {"clicksToday": 0, "totalClicks": 0}
                cfg["stats"]["clicksToday"] = cfg["stats"].get("clicksToday", 0) + 1
                cfg["stats"]["totalClicks"] = cfg["stats"].get("totalClicks", 0) + 1
                cfg["history"].insert(0, {
                    "title": click_data.get("title", "IndiaMART Requirement"),
                    "buyerLocation": click_data.get("location", "India"),
                    "orderValue": click_data.get("orderValue", "N/A"),
                    "timeFormatted": time.strftime("%I:%M:%S %p"),
                    "timestamp": int(time.time() * 1000)
                })
                cfg["history"] = cfg["history"][:200]
                save_config(cfg)
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"success": true}')
            except Exception:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def run_server():
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"Aguatech Dashboard Web Server running on http://0.0.0.0:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
