/**
 * IndiaMart Lead Autoclick Pro - Storage & State Management
 */

const DEFAULT_SETTINGS = {
  engineActive: false,
  soundEnabled: true,
  autoRefreshEnabled: true,
  refreshInterval: 15, // seconds
  showOnScreenTimer: true,
  globalDailyClickLimit: 0, // 0 = unlimited
  globalMinOrderValue: 0, // 0 = no min
  excludeRetailLeads: false,
  filterOnlyVerified: false,
  verificationTypes: {
    gst: false,
    phone: false,
    email: false,
    whatsapp: false,
    website: false
  },
  useNegativeKeywords: false,
  useLocations: false,
  useBlockedLocations: false,
  useExportCountries: false,
  useCategories: false,
  keywordSorting: 'entry', // 'entry' or 'name'
  categorySorting: 'entry',
  locationSorting: 'entry'
};

const DEFAULT_KEYWORDS = [
  {
    id: "kw-1",
    keyword: "Electric Stacker",
    minQty: 1,
    unit: "Piece",
    category: "",
    dailyLimit: 0,
    minOrderValue: 0,
    targetLocation: "",
    clicksToday: 0
  },
  {
    id: "kw-2",
    keyword: "Scissor lift",
    minQty: 1,
    unit: "Piece",
    category: "",
    dailyLimit: 0,
    minOrderValue: 0,
    targetLocation: "",
    clicksToday: 0
  },
  {
    id: "kw-3",
    keyword: "electric forklift",
    minQty: 1,
    unit: "Piece",
    category: "",
    dailyLimit: 0,
    minOrderValue: 0,
    targetLocation: "",
    clicksToday: 0
  },
  {
    id: "kw-4",
    keyword: "industrial Reach Truck",
    minQty: 1,
    unit: "Piece",
    category: "",
    dailyLimit: 0,
    minOrderValue: 0,
    targetLocation: "",
    clicksToday: 0
  },
  {
    id: "kw-5",
    keyword: "Goods Lift",
    minQty: 1,
    unit: "Piece",
    category: "",
    dailyLimit: 0,
    minOrderValue: 0,
    targetLocation: "",
    clicksToday: 0
  }
];

export class StorageManager {
  static getTodayString() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  static async getState() {
    return new Promise((resolve) => {
      chrome.storage.local.get([
        'settings',
        'keywords',
        'categories',
        'negativeKeywords',
        'locations',
        'blockedLocations',
        'exportCountries',
        'productCountryRules',
        'productLocationRules',
        'stats',
        'history',
        'clickedLeadIds'
      ], (res) => {
        const today = StorageManager.getTodayString();
        let stats = res.stats || { clicksToday: 0, totalClicks: 0, lastResetDate: today };
        let keywords = res.keywords || DEFAULT_KEYWORDS;
        let history = res.history || [];

        // Midnight reset check
        if (stats.lastResetDate !== today) {
          stats.clicksToday = 0;
          stats.lastResetDate = today;
          keywords = keywords.map(k => ({ ...k, clicksToday: 0 }));
          // Keep only today's history or preserve older as needed
          history = history.filter(h => {
            const hDate = new Date(h.timestamp);
            const hDateStr = `${hDate.getFullYear()}-${String(hDate.getMonth() + 1).padStart(2, '0')}-${String(hDate.getDate()).padStart(2, '0')}`;
            return hDateStr === today;
          });
          chrome.storage.local.set({ stats, keywords, history });
        }

        resolve({
          settings: { ...DEFAULT_SETTINGS, ...(res.settings || {}) },
          keywords,
          categories: res.categories || [],
          negativeKeywords: res.negativeKeywords || [],
          locations: res.locations || [],
          blockedLocations: res.blockedLocations || [],
          exportCountries: res.exportCountries || [],
          productCountryRules: res.productCountryRules || [],
          productLocationRules: res.productLocationRules || [],
          stats,
          history,
          clickedLeadIds: res.clickedLeadIds || []
        });
      });
    });
  }

  static async saveState(partialState) {
    return new Promise((resolve) => {
      chrome.storage.local.set(partialState, () => {
        resolve(true);
      });
    });
  }

  static async recordClick(leadData) {
    const state = await StorageManager.getState();
    const today = StorageManager.getTodayString();

    state.stats.clicksToday += 1;
    state.stats.totalClicks = (state.stats.totalClicks || 0) + 1;
    state.stats.lastResetDate = today;

    if (leadData.keyword) {
      const kw = state.keywords.find(k => k.keyword.toLowerCase() === leadData.keyword.toLowerCase());
      if (kw) {
        kw.clicksToday = (kw.clicksToday || 0) + 1;
      }
    }

    const historyItem = {
      id: 'click-' + Date.now() + '-' + Math.random().toString(36).substr(2, 5),
      timestamp: Date.now(),
      timeFormatted: new Date().toLocaleTimeString(),
      title: leadData.title || 'BuyLead Requirement',
      buyerLocation: leadData.location || 'India',
      keyword: leadData.keyword || 'General',
      quantity: leadData.quantity || 'N/A',
      orderValue: leadData.orderValue || 'N/A',
      status: 'CLICKED'
    };

    const updatedHistory = [historyItem, ...(state.history || [])].slice(0, 200);
    const toAdd = [leadData.leadId, leadData.titleKey].filter(Boolean);
    const updatedClickedIds = [...(state.clickedLeadIds || []), ...toAdd].slice(-500);

    await StorageManager.saveState({
      stats: state.stats,
      keywords: state.keywords,
      history: updatedHistory,
      clickedLeadIds: updatedClickedIds
    });

    return { stats: state.stats, historyItem };
  }
}

