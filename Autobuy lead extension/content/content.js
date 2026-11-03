/**
 * IndiaMart Lead Autoclick Pro - Main Content Script Engine
 */

(function () {
  'use strict';

  if (window.__IM_AUTOCLICK_INITIALIZED__) return;
  window.__IM_AUTOCLICK_INITIALIZED__ = true;

  let state = {
    settings: {
      engineActive: false,
      soundEnabled: true,
      autoRefreshEnabled: true,
      refreshInterval: 15,
      showOnScreenTimer: true,
      globalDailyClickLimit: 0,
      globalMinOrderValue: 0,
      excludeRetailLeads: false,
      filterOnlyVerified: false,
      verificationTypes: {},
      useNegativeKeywords: false,
      useLocations: false,
      useBlockedLocations: false,
      useExportCountries: false,
      useCategories: false
    },
    keywords: [],
    categories: [],
    negativeKeywords: [],
    locations: [],
    blockedLocations: [],
    exportCountries: [],
    productCountryRules: [],
    productLocationRules: [],
    stats: { clicksToday: 0, totalClicks: 0 },
    history: [],
    clickedLeadIds: []
  };

  let scanIntervalId = null;
  let countdownTimerId = null;
  let remainingSeconds = 15;
  let isScanning = false;
  let isPausedByUser = false;
  let lastScanSummary = 'Ready. Waiting for first scan...';

  // Track leads clicked in current session
  const sessionClickedIds = new Set();

  function shouldRunOnThisPage() {
    const href = window.location.href.toLowerCase();
    // Do not run on Message Centre / Chat / Settings
    if (href.includes('/messagecentre') || href.includes('/messages') || href.includes('/chat') || href.includes('/profile') || href.includes('/billing') || href.includes('/settings')) {
      return false;
    }
    return true;
  }

  /**
   * Load initial state and initialize UI & watchers
   */
  async function init() {
    if (!shouldRunOnThisPage()) return;

    try {
      chrome.storage.local.get(null, (res) => {
        if (res) {
          state = {
            ...state,
            ...res,
            settings: { ...state.settings, ...(res.settings || {}) },
            stats: res.stats || { clicksToday: 0, totalClicks: 0 },
            clickedLeadIds: res.clickedLeadIds || []
          };
          remainingSeconds = state.settings.refreshInterval || 15;
        }

        buildHUD();
        startScanLoop();
        startCountdownTimer();
      });

      chrome.storage.onChanged.addListener((changes, area) => {
        if (area !== 'local') return;
        for (const [key, { newValue }] of Object.entries(changes)) {
          if (key === 'settings') {
            state.settings = { ...state.settings, ...(newValue || {}) };
            updateHUD();
          } else {
            state[key] = newValue;
          }
        }
      });

      chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
        if (msg.action === 'SCAN_PAGE_NOW') {
          scanPage(true);
          sendResponse({ success: true, message: 'Scan initiated' });
        } else if (msg.action === 'GET_CONTENT_STATUS') {
          sendResponse({
            active: state.settings.engineActive,
            clicksToday: state.stats.clicksToday,
            nextRefresh: remainingSeconds
          });
        }
      });
    } catch (err) {
      console.error('[IM-Autoclick] Init error:', err);
    }
  }

  /**
   * Scanning Engine
   */
  async function scanPage(isManualTrigger = false) {
    if (!state.settings.engineActive && !isManualTrigger) return;
    if (isScanning) return;
    isScanning = true;

    try {
      const cards = LeadCardParser.findLeadCards();
      const kwNames = (state.keywords || []).map(k => k.keyword);

      if (!cards || cards.length === 0) {
        lastScanSummary = `No lead cards detected on this page.`;
        updateHUD();
        isScanning = false;
        return;
      }

      let matchedCount = 0;
      let firstSkipReason = '';

      for (let i = 0; i < cards.length; i++) {
        const card = cards[i];
        if (card.dataset.autoclicked === 'true') continue;

        const lead = LeadCardParser.parseCard(card);
        if (!lead || !lead.button) continue;

        const titleKey = 'title:' + (lead.title || '').trim().toLowerCase().replace(/[^a-z0-9]/g, '');

        if (
          sessionClickedIds.has(lead.leadId) ||
          sessionClickedIds.has(titleKey) ||
          (state.clickedLeadIds && (state.clickedLeadIds.includes(lead.leadId) || state.clickedLeadIds.includes(titleKey)))
        ) {
          continue;
        }

        // Match against user rules
        const evaluation = LeadMatcher.evaluate(lead, state);

        if (evaluation.match) {
          console.log('[IM-Autoclick] Matched card #' + (i + 1) + ':', lead.title, 'Keyword:', evaluation.matchedKeyword.keyword);
          highlightCard(card, evaluation.matchedKeyword.keyword);
          lead.keyword = evaluation.matchedKeyword.keyword;
          lead.titleKey = titleKey;

          // Safe human delay before initiating Step 1
          const delay = Math.floor(Math.random() * 400) + 500;
          await new Promise((r) => setTimeout(r, delay));

          // Execute 2-step purchase (Step 1: Contact Buyer Now -> Step 2: Send Reply)
          const purchaseSuccess = await completeLeadPurchase(lead);

          if (purchaseSuccess) {
            // ONLY record as clicked if purchase flow was fully confirmed
            sessionClickedIds.add(lead.leadId);
            sessionClickedIds.add(titleKey);
            card.dataset.autoclicked = 'true';
            matchedCount++;
          } else {
            // Purchase was incomplete; allow re-trying
            delete card.dataset.autoclicked;
            console.warn('[IM-Autoclick] Purchase incomplete for:', lead.title);
          }

          await new Promise((r) => setTimeout(r, 1200));
        } else {
          if (!firstSkipReason) {
            firstSkipReason = evaluation.reason;
          }
        }
      }

      if (matchedCount > 0) {
        lastScanSummary = `Found ${cards.length} cards. Clicked ${matchedCount} matching lead(s)!`;
      } else {
        lastScanSummary = `Found ${cards.length} cards. 0 matched. (${firstSkipReason || 'Check keywords'})`;
      }
      updateHUD();
    } catch (e) {
      console.warn('[IM-Autoclick] Scan error:', e);
    } finally {
      isScanning = false;
    }
  }

  /**
   * Complete 2-step purchase:
   * Step 1: Click "Contact Buyer Now" on the lead card.
   * Step 2: Detect the quotation/reply modal and click "Send Reply".
   */
  async function completeLeadPurchase(lead) {
    console.log('[IM-Autoclick] Step 1: Clicking Contact Buyer Now for:', lead.title, lead.button);
    showToast(`⚡ Step 1/2: Contacting ${lead.title}...`);

    // Step 1: Click the card's Contact Buyer Now button
    const clicked = triggerClick(lead.button);
    if (!clicked) {
      console.warn('[IM-Autoclick] Could not trigger click on lead button:', lead.button);
      return false;
    }

    // Step 2: Wait for modal view and click "Send Reply"
    console.log('[IM-Autoclick] Step 2: Waiting for "Send Reply" modal view...');
    const replied = await waitForAndClickSendReply();

    if (replied) {
      console.log('[IM-Autoclick] Step 2 SUCCESS: "Send Reply" clicked for:', lead.title);
      showToast(`🎉 Step 2/2 Complete: Sent Reply for ${lead.title}! Converted to Lead!`);

      if (state.settings.soundEnabled && window.SoundNotifier) {
        window.SoundNotifier.playSuccessChime();
      }

      // Record in storage ONLY when "Send Reply" is confirmed
      chrome.runtime.sendMessage({
        action: 'RECORD_CLICK',
        data: {
          leadId: lead.leadId,
          titleKey: lead.titleKey,
          title: lead.title,
          location: lead.location,
          keyword: lead.keyword,
          quantity: `${lead.quantity} ${lead.unit}`,
          orderValue: lead.orderValue ? `₹ ${lead.orderValue.toLocaleString('en-IN')}` : 'N/A'
        }
      });
      return true;
    } else {
      console.warn('[IM-Autoclick] Modal or "Send Reply" button was not found within timeout.');
      showToast(`⚠️ Lead opened! Click "Send Reply" on screen to complete: ${lead.title}`);
      return false;
    }
  }

  function triggerClick(el) {
    if (!el) return false;
    try {
      el.scrollIntoView({ behavior: 'auto', block: 'center' });
      if (typeof el.focus === 'function') el.focus();

      // Dispatch full mouse event cycle for React / AngularJS / jQuery
      const mousedown = new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window });
      const mouseup = new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window });
      const clickEvt = new MouseEvent('click', { bubbles: true, cancelable: true, view: window });

      el.dispatchEvent(mousedown);
      el.dispatchEvent(mouseup);
      el.dispatchEvent(clickEvt);

      if (typeof el.click === 'function') {
        el.click();
      }
      return true;
    } catch (e) {
      try { el.click(); return true; } catch (err) { return false; }
    }
  }

  /**
   * Step 2: Wait for modal view to open and click "Send Reply"
   */
  async function waitForAndClickSendReply() {
    // Poll every 250ms for up to 9 seconds (36 attempts)
    for (let attempt = 0; attempt < 36; attempt++) {
      await new Promise(r => setTimeout(r, 250));

      const allClickable = Array.from(document.querySelectorAll('button, a, input[type="button"], input[type="submit"], div[role="button"], span.btn, span'));

      for (const el of allClickable) {
        if (el.offsetWidth === 0 || el.offsetHeight === 0) continue;

        const rawText = (el.innerText || el.textContent || el.value || '').replace(/\s+/g, ' ').trim().toLowerCase();

        // Check specifically for "Send Reply" (as seen on IndiaMart) or fallback variants
        if (
          rawText === 'send reply' ||
          rawText.startsWith('send reply') ||
          rawText === 'send quotation' ||
          rawText.startsWith('send quotation') ||
          rawText === 'confirm contact' ||
          rawText === 'submit reply'
        ) {
          console.log('[IM-Autoclick] Found and clicking Modal Button:', rawText, el);
          await new Promise(r => setTimeout(r, 350));
          triggerClick(el);
          await new Promise(r => setTimeout(r, 600));
          return true;
        }
      }
    }
    return false;
  }

  function highlightCard(card, keyword) {
    card.classList.add('im-autoclick-matched-card');
    const badge = document.createElement('div');
    badge.className = 'im-autoclick-badge';
    badge.innerText = `Matched: ${keyword}`;
    card.style.position = 'relative';
    card.appendChild(badge);
  }

  function showToast(text) {
    let toast = document.getElementById('im-autoclick-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'im-autoclick-toast';
      document.body.appendChild(toast);
    }
    toast.innerText = text;
    toast.style.display = 'block';
    setTimeout(() => {
      toast.style.display = 'none';
    }, 4500);
  }

  /**
   * HUD Overlay
   */
  function buildHUD() {
    let hud = document.getElementById('im-autoclick-hud');
    if (hud) return;

    hud = document.createElement('div');
    hud.id = 'im-autoclick-hud';

    hud.innerHTML = `
      <div class="im-hud-header">
        <div class="im-hud-title">
          <span>⚡ IndiaMart Autoclick</span>
        </div>
        <div class="im-hud-controls">
          <button class="im-hud-btn" id="im-hud-reset-btn" title="Reset today's click memory and history">🔄 Reset</button>
          <button class="im-hud-btn primary" id="im-hud-inspect-btn" title="Inspect what cards are detected">🔍 Inspect</button>
          <button class="im-hud-btn" id="im-hud-scan-btn" title="Scan Page Now">Scan</button>
          <button class="im-hud-btn" id="im-hud-min-btn" title="Minimize/Expand">_</button>
        </div>
      </div>
      <div class="im-hud-body" id="im-hud-body">
        <div class="im-hud-status-row">
          <div class="im-status-left">
            <span class="im-status-dot" id="im-hud-dot"></span>
            <span id="im-hud-status-text">Engine Paused</span>
          </div>
          <span style="font-size: 11px; color: #94a3b8;" id="im-hud-kw-count">Keywords: 0</span>
        </div>
        <div class="im-hud-diag" id="im-hud-diag-text">${lastScanSummary}</div>
        <div class="im-hud-timer-bar-container" id="im-hud-timer-wrap">
          <div class="im-hud-timer-bar" id="im-hud-bar"></div>
        </div>
        <div class="im-hud-stats">
          <span>Today: <b id="im-hud-clicks">0</b></span>
          <span id="im-hud-countdown">Next refresh: 15s</span>
        </div>
      </div>
    `;

    document.body.appendChild(hud);

    // Event listeners
    document.getElementById('im-hud-reset-btn').addEventListener('click', () => {
      if (confirm("Reset today's click memory and allow re-clicking matching leads?")) {
        resetAllClicksMemory();
      }
    });

    document.getElementById('im-hud-scan-btn').addEventListener('click', () => {
      scanPage(true);
    });

    document.getElementById('im-hud-inspect-btn').addEventListener('click', () => {
      openInspectModal();
    });

    const minBtn = document.getElementById('im-hud-min-btn');
    minBtn.addEventListener('click', () => {
      const isMin = hud.classList.toggle('minimized');
      document.getElementById('im-hud-body').style.display = isMin ? 'none' : 'block';
      minBtn.innerText = isMin ? '□' : '_';
    });

    window.addEventListener('scroll', resetRefreshActivity, { passive: true });
    window.addEventListener('mousemove', resetRefreshActivity, { passive: true });

    updateHUD();
  }

  function resetAllClicksMemory() {
    sessionClickedIds.clear();
    state.clickedLeadIds = [];
    state.stats.clicksToday = 0;
    state.history = [];
    if (state.keywords) {
      state.keywords.forEach(k => { k.clicksToday = 0; });
    }
    document.querySelectorAll('[data-autoclicked]').forEach(el => {
      delete el.dataset.autoclicked;
    });
    chrome.runtime.sendMessage({ action: 'RESET_TODAY_CLICKS' }, () => {
      showToast('🔄 Memory reset: Clicks and lead history cleared to 0!');
      updateHUD();
      if (document.getElementById('im-inspect-modal')) {
        openInspectModal();
      }
    });
  }

  /**
   * Inspect Modal: Displays every detected card and why it matched or skipped
   */
  function openInspectModal() {
    try {
      closeInspectModal();

      const backdrop = document.createElement('div');
      backdrop.id = 'im-inspect-backdrop';
      backdrop.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.75);z-index:2147483646;';

      const modal = document.createElement('div');
      modal.id = 'im-inspect-modal';
      modal.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);z-index:2147483647;background:#0f172a;color:#f8fafc;border:1px solid #334155;border-radius:12px;width:720px;max-width:95vw;max-height:85vh;box-shadow:0 25px 50px -12px rgba(0,0,0,0.8);display:flex;flex-direction:column;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:13px;';

      let cards = [];
      try {
        cards = LeadCardParser.findLeadCards();
      } catch (findErr) {
        console.error('[IM-Autoclick] findLeadCards error:', findErr);
      }

      const activeKwList = (state.keywords || []).map(k => `"${k.keyword}"`).join(', ');

      let cardsHtml = '';
      if (!cards || cards.length === 0) {
        cardsHtml = `
          <div style="padding: 30px; text-align: center; color: #94a3b8;">
            <p style="font-size: 16px; margin-bottom: 8px;">⚠️ No BuyLead cards detected on this page view.</p>
            <p style="font-size: 12px;">Make sure leads have loaded on your screen.</p>
          </div>
        `;
      } else {
        cards.forEach((card, idx) => {
          try {
            const lead = LeadCardParser.parseCard(card);
            if (!lead) {
              const preview = (card.innerText || '').slice(0, 80).replace(/\s+/g, ' ');
              cardsHtml += `
                <div class="im-inspect-card-item skip">
                  <div class="im-inspect-title">#${idx + 1}: Unrecognized Card Structure</div>
                  <div class="im-inspect-meta"><span>Preview: "${escapeHtml(preview)}"</span></div>
                  <div class="im-inspect-reason skip">⏭️ SKIPPED: Card could not be parsed as a BuyLead.</div>
                </div>
              `;
              return;
            }

            const titleKey = 'title:' + (lead.title || '').trim().toLowerCase().replace(/[^a-z0-9]/g, '');
            const alreadyClicked = sessionClickedIds.has(lead.leadId) ||
              sessionClickedIds.has(titleKey) ||
              (state.clickedLeadIds && (state.clickedLeadIds.includes(lead.leadId) || state.clickedLeadIds.includes(titleKey)));

            const evalResult = LeadMatcher.evaluate(lead, state);
            const isMatch = evalResult.match;

            cardsHtml += `
              <div class="im-inspect-card-item ${isMatch && !alreadyClicked ? 'match' : 'skip'}">
                <div class="im-inspect-title">#${idx + 1}: ${escapeHtml(lead.title)}</div>
                <div class="im-inspect-meta">
                  <span><b>Qty:</b> ${lead.quantity} ${escapeHtml(lead.unit)}</span>
                  <span><b>Location:</b> ${escapeHtml(lead.location)}</span>
                  <span><b>Value:</b> ${lead.orderValue ? '₹ ' + lead.orderValue.toLocaleString('en-IN') : 'N/A'}</span>
                  <span><b>Button:</b> ${lead.button ? '✔ Found' : '❌ Not Found'}</span>
                </div>
                <div class="im-inspect-reason ${isMatch && !alreadyClicked ? 'match' : 'skip'}">
                  ${alreadyClicked ? 'ℹ️ ALREADY CONTACTED TODAY' : (isMatch ? '✔ MATCHED: ' + escapeHtml(evalResult.reason) : '⏭️ SKIPPED: ' + escapeHtml(evalResult.reason))}
                </div>
              </div>
            `;
          } catch (cErr) {
            console.error('[IM-Autoclick] Error parsing card in inspector:', cErr);
            cardsHtml += `
              <div class="im-inspect-card-item skip">
                <div class="im-inspect-title">#${idx + 1}: Card Parsing Error</div>
                <div class="im-inspect-reason skip">❌ Error: ${escapeHtml(cErr.message)}</div>
              </div>
            `;
          }
        });
      }

      if (!cardsHtml.trim()) {
        cardsHtml = `
          <div style="padding: 30px; text-align: center; color: #94a3b8;">
            <p style="font-size: 15px; margin-bottom: 8px;">No card details could be displayed.</p>
          </div>
        `;
      }

      modal.innerHTML = `
        <div class="im-inspect-head">
          <div>
            <h3 style="margin: 0; font-size: 15px;">🔍 Live Page Lead Inspector (${cards.length} cards detected)</h3>
            <span style="font-size: 11px; color: #94a3b8;">Active Keywords: [ ${activeKwList || 'None configured'} ]</span>
          </div>
          <div style="display:flex;align-items:center;gap:10px;">
            <button id="im-inspect-reset-btn" style="background:#dc2626;border:none;color:#ffffff;padding:5px 11px;border-radius:5px;font-size:11px;font-weight:600;cursor:pointer;">🔄 Reset Memory / Clicks</button>
            <button id="im-close-inspect-btn" style="background: none; border: none; color: #94a3b8; font-size: 20px; cursor: pointer;">✕</button>
          </div>
        </div>
        <div class="im-inspect-body">
          ${cardsHtml}
        </div>
      `;

      backdrop.addEventListener('click', closeInspectModal);
      document.body.appendChild(backdrop);
      document.body.appendChild(modal);

      document.getElementById('im-inspect-reset-btn').addEventListener('click', () => {
        resetAllClicksMemory();
      });

      document.getElementById('im-close-inspect-btn').addEventListener('click', closeInspectModal);
    } catch (globalErr) {
      console.error('[IM-Autoclick] openInspectModal error:', globalErr);
      alert('Could not open Inspector: ' + globalErr.message);
    }
  }

  function closeInspectModal() {
    const b = document.getElementById('im-inspect-backdrop');
    const m = document.getElementById('im-inspect-modal');
    if (b) b.remove();
    if (m) m.remove();
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.innerText = text || '';
    return div.innerHTML;
  }

  let activityTimeout = null;
  function resetRefreshActivity() {
    if (!state.settings.engineActive) return;
    isPausedByUser = true;
    clearTimeout(activityTimeout);
    activityTimeout = setTimeout(() => {
      isPausedByUser = false;
    }, 4000);
  }

  function updateHUD() {
    const hud = document.getElementById('im-autoclick-hud');
    if (!hud) return;

    const dot = document.getElementById('im-hud-dot');
    const statusText = document.getElementById('im-hud-status-text');
    const clicks = document.getElementById('im-hud-clicks');
    const timerWrap = document.getElementById('im-hud-timer-wrap');
    const diagText = document.getElementById('im-hud-diag-text');
    const kwCount = document.getElementById('im-hud-kw-count');

    if (state.settings.showOnScreenTimer === false) {
      hud.style.display = 'none';
      return;
    } else {
      hud.style.display = 'block';
    }

    if (kwCount) {
      kwCount.innerText = `Keywords: ${(state.keywords || []).length}`;
    }

    if (diagText) {
      diagText.innerText = lastScanSummary;
    }

    if (state.settings.engineActive) {
      dot.classList.add('active');
      statusText.innerText = 'Active - Auto-clicking';
      statusText.style.color = '#4ade80';
    } else {
      dot.classList.remove('active');
      statusText.innerText = 'Engine Paused';
      statusText.style.color = '#94a3b8';
    }

    if (!state.settings.autoRefreshEnabled) {
      timerWrap.style.display = 'none';
    } else {
      timerWrap.style.display = 'block';
    }

    const limitStr = state.settings.globalDailyClickLimit > 0 ? `/${state.settings.globalDailyClickLimit}` : '';
    clicks.innerText = `${state.stats.clicksToday || 0}${limitStr}`;
  }

  /**
   * Scan Loop (scans every 2.5 seconds)
   */
  function startScanLoop() {
    if (scanIntervalId) clearInterval(scanIntervalId);
    scanIntervalId = setInterval(() => {
      if (state.settings.engineActive) {
        scanPage();
      }
    }, 2500);

    setTimeout(() => {
      if (state.settings.engineActive) scanPage();
    }, 1200);
  }

  /**
   * Auto-Refresh Countdown
   */
  function startCountdownTimer() {
    if (countdownTimerId) clearInterval(countdownTimerId);

    countdownTimerId = setInterval(() => {
      if (!state.settings.engineActive || !state.settings.autoRefreshEnabled) {
        const cdEl = document.getElementById('im-hud-countdown');
        if (cdEl) cdEl.innerText = 'Auto-refresh off';
        return;
      }

      if (isPausedByUser) {
        const cdEl = document.getElementById('im-hud-countdown');
        if (cdEl) cdEl.innerText = 'User active (waiting)';
        return;
      }

      remainingSeconds--;

      const cdEl = document.getElementById('im-hud-countdown');
      const bar = document.getElementById('im-hud-bar');

      if (cdEl) cdEl.innerText = `Refresh in ${Math.max(0, remainingSeconds)}s`;
      if (bar) {
        const percent = Math.max(0, (remainingSeconds / (state.settings.refreshInterval || 15)) * 100);
        bar.style.width = `${percent}%`;
      }

      if (remainingSeconds <= 0) {
        remainingSeconds = state.settings.refreshInterval || 15;
        window.location.reload();
      }
    }, 1000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
