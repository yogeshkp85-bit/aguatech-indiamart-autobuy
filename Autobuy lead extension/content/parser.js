/**
 * IndiaMart Lead Autoclick Pro - Resilient DOM Card Parser
 * Extracts structured data from IndiaMart BuyLead cards across all desktop, seller, and mobile layouts.
 */

class LeadCardParser {
  /**
   * Determine if an element acts as a Contact Buyer action button
   */
  static isContactButton(el) {
    if (!el || !el.tagName) return false;
    const tag = el.tagName.toUpperCase();

    // Must be a clickable element
    if (!['BUTTON', 'A', 'INPUT', 'DIV', 'SPAN'].includes(tag)) return false;

    const rawText = (el.textContent || el.innerText || el.value || '');
    const text = rawText.replace(/\s+/g, ' ').trim().toLowerCase();
    const cls = (el.className || '').toString().toLowerCase();
    const id = (el.id || '').toLowerCase();
    const onclick = (el.getAttribute('onclick') || '').toLowerCase();
    const dataClick = (el.getAttribute('data-click') || '').toLowerCase();

    // Skip utility, filter, or buyer detail elements
    if (
      text.includes('login') ||
      text.includes('sign in') ||
      text.includes('search') ||
      text.includes('menu') ||
      text.includes('filter') ||
      text.includes('shortlist') ||
      text.includes('view similar') ||
      text.includes('hide') ||
      text.includes('not relevant') ||
      text.includes('verified') ||
      text.includes('electrical') ||
      text.includes('member')
    ) {
      return false;
    }

    // Specific contact button action phrases
    const matchPhrases = [
      'contact buyer now',
      'contact buyer',
      'contact now',
      'send quotation',
      'send quote',
      'send reply',
      'call buyer',
      'get buyer details'
    ];

    for (const phrase of matchPhrases) {
      if (text === phrase || text.startsWith(phrase)) {
        return true;
      }
    }

    // Explicit IndiaMart class / id patterns for the contact button
    if (
      cls.includes('cbn') ||
      cls.includes('contact-buyer') ||
      cls.includes('contactbuyer') ||
      cls.includes('bl_btn') ||
      id.includes('cbn') ||
      id.includes('contact_buyer') ||
      onclick.includes('cbn') ||
      dataClick.includes('cbn')
    ) {
      return true;
    }

    return false;
  }

  /**
   * Walk up from a Contact button to find its enclosing Lead Card container.
   * Invariant: A single lead card contains at most 1 or 2 contact buttons (e.g. Call & Contact).
   * A page list container contains many buttons.
   */
  static getCardContainerForButton(btn) {
    let current = btn.parentElement;
    let candidate = current;

    while (current && current !== document.body && current !== document.documentElement) {
      const cl = (current.className || '').toString().toLowerCase();
      const id = (current.id || '').toLowerCase();
      const tag = current.tagName;

      // Known explicit card class patterns
      const isExplicitCard = (
        cl.includes('bl_card') ||
        cl.includes('bl-card') ||
        cl.includes('m-card') ||
        cl.includes('gl-card') ||
        cl.includes('lead_card') ||
        cl.includes('lead-card') ||
        cl.includes('card-listing') ||
        cl.includes('listing_card') ||
        cl.includes('bl_row') ||
        cl.includes('bl-row') ||
        cl.includes('bl_lst_row') ||
        cl.includes('eq_card') ||
        cl.includes('enq-card') ||
        id.startsWith('bl_') ||
        id.startsWith('lead_') ||
        id.startsWith('card_') ||
        Boolean(current.dataset && (current.dataset.leadid || current.dataset.blid)) ||
        tag === 'ARTICLE' ||
        tag === 'LI'
      );

      // Check how many contact buttons are inside current
      const allClickable = Array.from(current.querySelectorAll('button, a, input, div[role="button"], span'));
      const contactBtnsInside = allClickable.filter(el => LeadCardParser.isContactButton(el));

      // If current contains more than 2 contact buttons, we have exited the individual card!
      if (contactBtnsInside.length > 2) {
        break;
      }

      if (isExplicitCard) {
        candidate = current;
        break;
      }

      // If it's a div with reasonable card dimensions (height between 60px and 1200px)
      if (current.offsetHeight >= 60 && current.offsetHeight < 1200) {
        candidate = current;
      }

      current = current.parentElement;
    }

    return candidate;
  }

  /**
   * Find all lead cards on the page using multiple fallback strategies
   */
  static findLeadCards() {
    const foundCards = new Set();

    // Strategy 1: Look for explicit class containers
    const primarySelectors = [
      '.bl_card', '.bl-card', '.m-card', '.gl-card', '.data-card',
      '[data-leadid]', '[data-blid]', '.card-listing', '.lead-card',
      '.lead_card', '.buyer-card', '.bl_row', '.bl-row', '.bl_lst_row',
      '.lst_rw', '.listing_card', '.enq-card', '.eq_card', '[id^="bl_"]', '[id^="lead_"]'
    ];

    for (const sel of primarySelectors) {
      try {
        const elements = document.querySelectorAll(sel);
        for (const el of elements) {
          if (el.offsetHeight > 50 && (el.innerText || '').trim().length > 15) {
            foundCards.add(el);
          }
        }
      } catch (e) { }
    }

    // Strategy 2: If no explicit cards found, discover them via Contact buttons!
    const allClickable = Array.from(document.querySelectorAll('button, a, input, div[role="button"], span.btn, span'));
    const contactButtons = allClickable.filter(el => this.isContactButton(el));

    for (const btn of contactButtons) {
      const card = this.getCardContainerForButton(btn);
      if (card && card.offsetHeight > 50) {
        foundCards.add(card);
      }
    }

    return Array.from(foundCards);
  }

  /**
   * Parse a single lead card DOM element into structured Lead data
   */
  static parseCard(cardEl) {
    if (!cardEl || !cardEl.innerText) return null;

    try {
      const fullText = cardEl.innerText;

      // Extract Contact Button
      const btn = this.findContactButton(cardEl);

      // Only mark as recommendation if it's an ad banner with no actionable contact button
      const isRecommendation = !btn && /buyer also viewed|similar requirements|suggested for you|frequently viewed together/i.test(fullText);

      // Extract Title safely
      let title = 'Unknown BuyLead';
      try {
        title = this.extractTitle(cardEl);
      } catch (e) { }

      // Extract Location & Country safely
      let location = 'India', country = 'India', isExport = false;
      try {
        const lObj = this.extractLocation(cardEl, fullText);
        location = lObj.location;
        country = lObj.country;
        isExport = lObj.isExport;
      } catch (e) { }

      // Extract unique Lead ID using content signature
      let leadId = 'gen-' + Date.now();
      try {
        leadId = this.extractLeadId(cardEl, fullText, title, location);
      } catch (e) { }

      // Extract Quantity & Unit safely
      let quantity = 1, unit = 'Piece', isUnspecified = true;
      try {
        const qObj = this.extractQuantity(cardEl, fullText);
        quantity = qObj.quantity;
        unit = qObj.unit;
        isUnspecified = qObj.isUnspecified;
      } catch (e) { }

      // Extract Order Value safely
      let orderValue = 0;
      try {
        orderValue = this.extractOrderValue(fullText);
      } catch (e) { }

      // Extract Verification Badges safely
      let verifications = { gst: false, phone: false, email: false, whatsapp: false, website: false };
      try {
        verifications = this.extractVerifications(cardEl, fullText);
      } catch (e) { }

      // Check if retail lead safely
      let isRetail = false;
      try {
        isRetail = this.checkIsRetail(fullText, quantity, unit);
      } catch (e) { }

      return {
        element: cardEl,
        button: btn,
        leadId,
        title,
        quantity,
        unit,
        isUnspecified,
        orderValue,
        location,
        country,
        isExport,
        verifications,
        isRetail,
        isRecommendation,
        rawText: fullText
      };
    } catch (err) {
      console.error('[IM-Autoclick] Critical error in parseCard:', err);
      return null;
    }
  }

  static findContactButton(cardEl) {
    if (!cardEl) return null;

    // Search explicitly for interactive elements inside the card
    const candidates = Array.from(cardEl.querySelectorAll('button, a, input[type="button"], input[type="submit"], [role="button"], .btn, span.btn, span'));

    // Priority 1: Exact or startsWith "Contact Buyer Now" or "Contact Buyer"
    for (const el of candidates) {
      if (el.offsetWidth === 0 || el.offsetHeight === 0) continue;
      const text = (el.innerText || el.textContent || el.value || '').replace(/\s+/g, ' ').trim().toLowerCase();
      if (text === 'contact buyer now' || text === 'contact buyer' || text === 'contact now') {
        return el;
      }
    }

    // Priority 2: Text starting with "contact buyer"
    for (const el of candidates) {
      if (el.offsetWidth === 0 || el.offsetHeight === 0) continue;
      const text = (el.innerText || el.textContent || el.value || '').replace(/\s+/g, ' ').trim().toLowerCase();
      if (text.startsWith('contact buyer') || text.startsWith('contact now')) {
        return el;
      }
    }

    // Priority 3: Class or attribute matching (cbn, bl_btn, contact-buyer)
    for (const el of candidates) {
      if (el.offsetWidth === 0 || el.offsetHeight === 0) continue;
      if (this.isContactButton(el)) {
        return el;
      }
    }

    return null;
  }

  static extractLeadId(cardEl, fullText, title, location) {
    // 1. Explicit lead ID on card element if specific
    if (cardEl.dataset && cardEl.dataset.leadid && cardEl.dataset.leadid.length > 3) {
      return 'bl-' + cardEl.dataset.leadid;
    }
    if (cardEl.dataset && cardEl.dataset.blid && cardEl.dataset.blid.length > 3) {
      return 'bl-' + cardEl.dataset.blid;
    }

    // 2. Explicit ID on the card itself (must NOT be generic container IDs like 'content', 'main', 'listing', etc.)
    if (cardEl.id && cardEl.id.length > 4 && !/^(content|main|container|wrapper|listing|body|table|row|card)$/i.test(cardEl.id)) {
      if (cardEl.id.includes('lead') || cardEl.id.includes('bl_') || cardEl.id.includes('card_')) {
        return 'bl-id-' + cardEl.id;
      }
    }

    // 3. Robust card-specific content signature
    // Uses Title + Location + Time text snippet to produce an unambiguous card hash
    const cleanTitle = (title || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    const cleanLoc = (location || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    const timeMatch = (fullText || '').match(/(\d+\s*(?:hrs?|mins?|days?|hours?|minutes?)\s*ago)/i);
    const timeStr = timeMatch ? timeMatch[1].replace(/\s+/g, '') : '';

    const signature = `${cleanTitle}_${cleanLoc}_${timeStr}`;

    let hash = 0;
    for (let i = 0; i < signature.length; i++) {
      hash = ((hash << 5) - hash) + signature.charCodeAt(i);
      hash |= 0;
    }

    return 'sig-' + Math.abs(hash) + '-' + cleanTitle.slice(0, 15);
  }

  /**
   * Filters out action toolbar links, technical specs, and utility labels from candidate titles
   */
  static isValidTitle(text) {
    if (!text || typeof text !== 'string') return false;
    const clean = text.replace(/\s+/g, ' ').trim();
    if (clean.length < 3 || clean.length > 120) return false;

    const lower = clean.toLowerCase();

    // Must not contain action toolbar words or status strings
    const forbiddenPhrases = [
      'view similar',
      'shortlist',
      'not relevant',
      'contact buyer',
      'send reply',
      'send quotation',
      'send quote',
      'call buyer',
      'get buyer details',
      'member since',
      'replies:',
      'replies :',
      'lifting capacity',
      'mounting type',
      'arm span',
      'probable requirement',
      'explore other leads',
      'buyer also viewed',
      'buyer details',
      'requirement type',
      'business use',
      'resale',
      'available :',
      'available:',
      'ago',
      'verified',
      'gst in',
      'gstin',
      'recommended',
      'bulk (',
      'explore other',
      'posted',
      'lead manager',
      'buyleads',
      'tenders',
      'past transactions'
    ];

    for (const phrase of forbiddenPhrases) {
      if (lower.includes(phrase)) {
        return false;
      }
    }

    // If it's literally "hide"
    if (lower === 'hide') return false;

    // Must not start with currency symbols
    if (/^[₹$€]/.test(clean) || lower.startsWith('rs') || lower.startsWith('inr')) {
      return false;
    }

    // Must contain letters
    if (!/[a-zA-Z]/.test(clean)) {
      return false;
    }

    return true;
  }

  /**
   * Extract Product / Requirement Name accurately, bypassing action toolbar buttons
   */
  static extractTitle(cardEl) {
    if (!cardEl) return 'Unknown BuyLead';

    // Strategy 1: Look for explicit headings (h1, h2, h3, h4)
    const headings = Array.from(cardEl.querySelectorAll('h1, h2, h3, h4'));
    for (const h of headings) {
      const text = (h.innerText || h.textContent || '').replace(/\s+/g, ' ').trim();
      if (this.isValidTitle(text)) {
        return text;
      }
    }

    // Strategy 2: Look for title or product class elements
    const titleClassElements = Array.from(cardEl.querySelectorAll(
      '.bl_title, .prd-name, .prd_name, .product-name, [class*="lead-title" i], [class*="lead_title" i], [class*="prd_name" i], [class*="prd-name" i]'
    ));
    for (const el of titleClassElements) {
      const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
      if (this.isValidTitle(text)) {
        return text;
      }
    }

    // Strategy 3: Check lines of cardEl.innerText
    // On IndiaMart, the very first text line of the card is almost always the requirement title
    const rawText = cardEl.innerText || '';
    const lines = rawText.split('\n')
      .map(l => l.replace(/\s+/g, ' ').trim())
      .filter(l => this.isValidTitle(l));

    if (lines.length > 0) {
      return lines[0];
    }

    // Strategy 4: Fallback to category breadcrumb if present (e.g. "Hydraulic Crane > Hydraulic Jib Crane")
    const breadcrumbMatch = rawText.match(/([A-Za-z\s]+>\s*([A-Za-z\s]+))/);
    if (breadcrumbMatch && breadcrumbMatch[2]) {
      const cand = breadcrumbMatch[2].trim();
      if (this.isValidTitle(cand)) {
        return cand;
      }
    }

    return 'Unknown BuyLead';
  }

  static extractQuantity(cardEl, fullText) {
    // Pattern: Explicit Quantity e.g. "Quantity: 500 Kilogram", "Qty: 10 Piece"
    const qtyRegex = /(?:Quantity|Qty|Required\s+Qty|Order\s+Quantity)\s*[:\-]?\s*([0-9.,\-]+)\s*([a-zA-Z]+)?/i;
    const match = fullText.match(qtyRegex);

    if (match) {
      const valStr = match[1].split('-')[0].replace(/,/g, '');
      const parsedQty = parseFloat(valStr) || 1;
      const parsedUnit = (match[2] || 'Piece').trim();
      return { quantity: parsedQty, unit: parsedUnit, isUnspecified: false };
    }

    // Strip technical specifications like "Lifting Capacity: 3 ton" or "Arm Span: 3 m"
    const cleanForQty = fullText.replace(/(?:Lifting Capacity|Capacity|Arm Span|Height|Power|Rating|Span)\s*[:\-]?\s*[0-9.,]+\s*(?:ton|tons|m|mtr|kg|hp|kva|v)\b/gi, '');

    // Inline packaging quantity check e.g. "100 Pcs", "50 Boxes", "10 Piece"
    const inlineMatch = cleanForQty.match(/\b([0-9]+)\s*(Piece|Pcs|Pieces|Box|Boxes|Set|Sets|Kit|Kits|Packet|Packets|Carton|Cartons|Strip|Strips|Bottle|Bottles|Pair|Pairs|Dozen)\b/i);
    if (inlineMatch) {
      return {
        quantity: parseFloat(inlineMatch[1]) || 1,
        unit: inlineMatch[2].trim(),
        isUnspecified: false
      };
    }

    // Default if buyer didn't specify order quantity
    return { quantity: 1, unit: 'Piece', isUnspecified: true };
  }

  static extractOrderValue(fullText) {
    if (!fullText) return 0;
    try {
      const valRegex = /(?:₹|Rs\.?|INR|Value\s*[:\-]?\s*₹?)\s*([0-9.,]+)\s*(Lakh|Lac|Lakhs|Lacs|Crore|Crores|Cr|k)?/i;
      const match = fullText.match(valRegex);
      if (!match) return 0;

      let num = parseFloat(match[1].replace(/,/g, '')) || 0;
      const multiplier = (match[2] || '').toLowerCase();

      if (multiplier.startsWith('l')) {
        num = num * 100000;
      } else if (multiplier.startsWith('cr')) {
        num = num * 10000000;
      } else if (multiplier === 'k') {
        num = num * 1000;
      }

      return Math.round(num);
    } catch (e) {
      return 0;
    }
  }

  static extractLocation(cardEl, fullText) {
    let locationStr = '';
    let country = 'India';
    let isExport = false;

    // 1. Explicit Location tag
    const locRegex = /(?:Location|Buyer Location|Member from|City|Delivered To|State)\s*[:\-]?\s*([a-zA-Z\s,]+)/i;
    const match = fullText.match(locRegex);
    if (match && match[1].trim()) {
      locationStr = match[1].split('\n')[0].trim();
    } else {
      // 2. Pattern on IndiaMart: "[time] ago [City], [State]" e.g. "23 hrs ago Moradabad, Uttar Pradesh"
      const timeLocMatch = fullText.match(/(?:hrs?|mins?|days?|hours?|minutes?|yesterday|today)\s+ago\s+([A-Za-z\s]+,\s*[A-Za-z\s]+)/i);
      if (timeLocMatch) {
        locationStr = timeLocMatch[1].split('\n')[0].trim();
      } else {
        // 3. City, State pattern anywhere in the card
        const cityStateMatch = fullText.match(/\b([A-Z][a-zA-Z\s]{2,15},\s*[A-Z][a-zA-Z\s]{2,20})\b/);
        if (cityStateMatch) {
          const cand = cityStateMatch[1].trim();
          if (!/not relevant|view similar|lifting capacity|business use/i.test(cand)) {
            locationStr = cand;
          }
        }
      }
    }

    // Check export countries
    const exportCountryNames = [
      'United States', 'USA', 'United Kingdom', 'UK', 'United Arab Emirates', 'UAE',
      'Dubai', 'Saudi Arabia', 'Canada', 'Australia', 'Germany', 'France',
      'Singapore', 'Malaysia', 'South Africa', 'Kenya', 'Nigeria', 'Oman', 'Qatar',
      'Kuwait', 'Bangladesh', 'Nepal', 'Sri Lanka', 'Vietnam', 'Philippines'
    ];

    for (const expCountry of exportCountryNames) {
      const countryRegex = new RegExp(`\\b${expCountry}\\b`, 'i');
      if (countryRegex.test(fullText) || (locationStr && countryRegex.test(locationStr))) {
        country = expCountry;
        isExport = true;
        break;
      }
    }

    if (fullText.toLowerCase().includes('export lead') || fullText.toLowerCase().includes('international lead')) {
      isExport = true;
    }

    return {
      location: locationStr || 'India',
      country,
      isExport
    };
  }

  static extractVerifications(cardEl, fullText) {
    const textLower = fullText.toLowerCase();
    return {
      gst: textLower.includes('gst verified') || textLower.includes('gstin verified') || textLower.includes('gstin'),
      phone: textLower.includes('mobile verified') || textLower.includes('phone verified') || textLower.includes('contact verified'),
      email: textLower.includes('email verified'),
      whatsapp: textLower.includes('whatsapp verified'),
      website: textLower.includes('website verified') || textLower.includes('trustseal') || textLower.includes('star supplier')
    };
  }

  static checkIsRetail(fullText, quantity, unit) {
    const textLower = fullText.toLowerCase();
    // Only classify as retail if it explicitly states personal use
    if (
      textLower.includes('retail lead') ||
      textLower.includes('retail requirement') ||
      textLower.includes('for personal use') ||
      textLower.includes('for home use') ||
      textLower.includes('single piece for personal') ||
      textLower.includes('only 1 piece required for personal')
    ) {
      return true;
    }
    return false;
  }
}

if (typeof window !== 'undefined') {
  window.LeadCardParser = LeadCardParser;
}
