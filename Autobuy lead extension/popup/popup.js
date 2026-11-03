/**
 * IndiaMart Lead Autoclick Pro - Popup Controller
 */

import { StorageManager } from '../utils/storage.js';

let currentState = null;

async function loadAndRender() {
  currentState = await StorageManager.getState();
  const { settings, stats, keywords } = currentState;

  // Stats
  const clicksTodayEl = document.getElementById('clicks-today-count');
  const limitSubtextEl = document.getElementById('clicks-limit-subtext');
  const totalClicksEl = document.getElementById('total-clicks-count');

  clicksTodayEl.innerText = stats.clicksToday || 0;
  if (settings.globalDailyClickLimit > 0) {
    limitSubtextEl.innerText = `/ ${settings.globalDailyClickLimit} daily limit`;
  } else {
    limitSubtextEl.innerText = `/ Unlimited clicks`;
  }
  totalClicksEl.innerText = `${stats.totalClicks || 0} total all-time`;

  // Engine Toggle
  const engineToggle = document.getElementById('engine-toggle');
  const engineStatusText = document.getElementById('engine-status-text');

  engineToggle.checked = !!settings.engineActive;
  if (settings.engineActive) {
    engineStatusText.innerText = 'Active - Auto-clicking';
    engineStatusText.style.color = '#4ade80';
  } else {
    engineStatusText.innerText = 'Engine Paused';
    engineStatusText.style.color = '#94a3b8';
  }

  // Quick Options
  document.getElementById('sound-toggle').checked = !!settings.soundEnabled;
  document.getElementById('autorefresh-toggle').checked = !!settings.autoRefreshEnabled;
  document.getElementById('refresh-interval-input').value = settings.refreshInterval || 15;
  document.getElementById('onscreen-timer-toggle').checked = settings.showOnScreenTimer !== false;

  // Render Keywords
  renderKeywords(keywords || []);
}

function renderKeywords(keywords) {
  const kwListEl = document.getElementById('keywords-list');
  const countEl = document.getElementById('keyword-count');
  countEl.innerText = keywords.length;

  kwListEl.innerHTML = '';
  if (keywords.length === 0) {
    kwListEl.innerHTML = '<div style="color: #64748b; font-size: 11px; text-align: center; padding: 8px;">No keywords added yet.</div>';
    return;
  }

  keywords.forEach((kw, index) => {
    const item = document.createElement('div');
    item.className = 'keyword-item';

    const limitStr = kw.dailyLimit > 0 ? `${kw.clicksToday || 0}/${kw.dailyLimit}` : `${kw.clicksToday || 0}/∞`;

    item.innerHTML = `
      <div class="kw-info">
        <span class="kw-name">${escapeHtml(kw.keyword)}</span>
        <span class="kw-badge">${limitStr}</span>
      </div>
      <button class="kw-delete-btn" data-index="${index}" title="Remove keyword">×</button>
    `;

    item.querySelector('.kw-delete-btn').addEventListener('click', async (e) => {
      e.stopPropagation();
      keywords.splice(index, 1);
      await StorageManager.saveState({ keywords });
      renderKeywords(keywords);
    });

    kwListEl.appendChild(item);
  });
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.innerText = text || '';
  return div.innerHTML;
}

// Bind Event Listeners
document.addEventListener('DOMContentLoaded', () => {
  loadAndRender();

  // Engine Switch
  const engineToggle = document.getElementById('engine-toggle');
  engineToggle.addEventListener('change', async () => {
    currentState.settings.engineActive = engineToggle.checked;
    await StorageManager.saveState({ settings: currentState.settings });
    loadAndRender();
  });

  // Sound Toggle
  document.getElementById('sound-toggle').addEventListener('change', async (e) => {
    currentState.settings.soundEnabled = e.target.checked;
    await StorageManager.saveState({ settings: currentState.settings });
  });

  // Auto-refresh Toggle
  document.getElementById('autorefresh-toggle').addEventListener('change', async (e) => {
    currentState.settings.autoRefreshEnabled = e.target.checked;
    await StorageManager.saveState({ settings: currentState.settings });
  });

  // Refresh Interval Input
  document.getElementById('refresh-interval-input').addEventListener('change', async (e) => {
    const val = parseInt(e.target.value, 10) || 15;
    currentState.settings.refreshInterval = Math.max(3, val);
    await StorageManager.saveState({ settings: currentState.settings });
  });

  // On-screen HUD Timer Toggle
  document.getElementById('onscreen-timer-toggle').addEventListener('change', async (e) => {
    currentState.settings.showOnScreenTimer = e.target.checked;
    await StorageManager.saveState({ settings: currentState.settings });
  });

  // Quick Add Keyword
  const quickAddBtn = document.getElementById('quick-add-kw-btn');
  const quickAddForm = document.getElementById('quick-add-form');
  const newKwInput = document.getElementById('new-kw-input');
  const saveNewKwBtn = document.getElementById('save-new-kw-btn');

  quickAddBtn.addEventListener('click', () => {
    quickAddForm.classList.toggle('hidden');
    if (!quickAddForm.classList.contains('hidden')) {
      newKwInput.focus();
    }
  });

  saveNewKwBtn.addEventListener('click', async () => {
    const val = newKwInput.value.trim();
    if (!val) return;

    currentState.keywords.push({
      id: 'kw-' + Date.now(),
      keyword: val,
      minQty: 1,
      unit: 'Piece',
      category: '',
      dailyLimit: 0,
      minOrderValue: 0,
      targetLocation: '',
      clicksToday: 0
    });

    await StorageManager.saveState({ keywords: currentState.keywords });
    newKwInput.value = '';
    quickAddForm.classList.add('hidden');
    renderKeywords(currentState.keywords);
  });

  newKwInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') saveNewKwBtn.click();
  });

  // Scan Page Now
  document.getElementById('scan-now-btn').addEventListener('click', async () => {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs && tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, { action: 'SCAN_PAGE_NOW' }, (resp) => {
        if (chrome.runtime.lastError) {
          alert('Please navigate to IndiaMart Seller BuyLeads page first:\nhttps://seller.indiamart.com/bl/');
        } else {
          window.close();
        }
      });
    }
  });

  // Open Full Dashboard
  const openDash = () => chrome.runtime.openOptionsPage();
  document.getElementById('open-dashboard-btn').addEventListener('click', openDash);
  document.getElementById('full-dashboard-btn').addEventListener('click', openDash);
});

