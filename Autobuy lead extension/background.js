/**
 * IndiaMart Lead Autoclick Pro - Background Service Worker
 */

import { StorageManager } from './utils/storage.js';

// Setup alarms on installation
chrome.runtime.onInstalled.addListener(async () => {
  // Initialize defaults
  const state = await StorageManager.getState();
  updateBadge(state);

  // Setup periodic check for midnight rollover
  chrome.alarms.create('midnightResetCheck', {
    periodInMinutes: 30
  });
});

// Periodic alarm handler for midnight rollover
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'midnightResetCheck') {
    const state = await StorageManager.getState();
    updateBadge(state);
  }
});

// Message listener
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'RECORD_CLICK') {
    StorageManager.recordClick(request.data).then(({ stats }) => {
      updateBadge({ stats });
      sendResponse({ success: true, stats });
    });
    return true; // Keep message channel open for async response
  }

  if (request.action === 'UPDATE_BADGE') {
    StorageManager.getState().then((state) => {
      updateBadge(state);
      sendResponse({ success: true });
    });
    return true;
  }

  if (request.action === 'OPEN_OPTIONS') {
    chrome.runtime.openOptionsPage();
    sendResponse({ success: true });
    return true;
  }

  if (request.action === 'RESET_TODAY_CLICKS') {
    StorageManager.getState().then(async (state) => {
      state.stats.clicksToday = 0;
      state.clickedLeadIds = [];
      state.history = [];
      if (state.keywords) {
        state.keywords.forEach(k => { k.clicksToday = 0; });
      }
      await StorageManager.saveState({
        stats: state.stats,
        clickedLeadIds: [],
        history: [],
        keywords: state.keywords
      });
      updateBadge(state);
      sendResponse({ success: true, stats: state.stats });
    });
    return true;
  }
});

function updateBadge(state) {
  try {
    const clicks = state.stats ? state.stats.clicksToday : 0;
    const text = clicks > 0 ? String(clicks) : '';
    chrome.action.setBadgeText({ text });
    chrome.action.setBadgeBackgroundColor({ color: '#16a34a' });
  } catch (e) {
    // Ignore in non-active contexts
  }
}

