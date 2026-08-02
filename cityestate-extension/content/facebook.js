/**
 * CityEstate Bridge — Facebook Content Script (Fixed)
 * ====================================================
 * Monitors Facebook Groups for buyer-intent posts.
 * Sends qualified leads to AI Brain via service worker.
 *
 * Fixes: sentinel guard, debounced observer, React-compatible posting,
 *        robust selectors, Arabic normalization, bounded dedup cache.
 */

(function () {
  "use strict";

  // Guard: prevent double injection
  if (window.__cityestate_loaded_fb) return;
  window.__cityestate_loaded_fb = true;

  // ---------------------------------------------------------------------------
  // Selectors — multiple fallbacks per element
  // ---------------------------------------------------------------------------
  const SELECTORS = {
    groupFeed: [
      'div[role="feed"]',
      'div[data-pagelet="Feed"]',
      'div[role="main"] > div > div',
    ],
    postContainer: [
      'div[role="article"]',
      'div[data-pagelet="FeedUnit"]',
      'div[class*="userContent"]',
    ],
    postText: [
      'div[data-ad-preview="message"]',
      'div[dir="auto"] span',
      'div[data-testid="post_message"]',
    ],
    postAuthor: [
      'h2 span a',
      'h3 span a',
      'a[role="link"][tabindex="0"] span',
      'strong span',
    ],
    postLink: [
      'a[href*="/posts/"]',
      'a[href*="/permalink/"]',
      'a[href*="/story.php"]',
    ],
    groupName: [
      'h1 span',
      'h2 span',
      'a[href*="/groups/"] span',
    ],
    postComposer: [
      'div[role="textbox"][contenteditable="true"]',
      'form [contenteditable="true"]',
      'div[aria-label="Write something..."]',
    ],
    postButton: [
      'div[aria-label="Post"]',
      'span[data-testid="post-button"]',
      'button[type="submit"]',
    ],
  };

  // ---------------------------------------------------------------------------
  // Egyptian Real Estate Keywords
  // ---------------------------------------------------------------------------
  const BUYER_SIGNALS = [
    "مطلوب", "مطلوب شقة", "مطلوب عقار", "مطلوب فيلا",
    "عايز", "أبحث", "أدور", "بدي", "محتاج",
    "حد يساعدني", "مهموم", "لو في حد",
    "ميزانية", "ميزانيتي", "أقدر أدفع",
    "استوديو", "غرفتين", "3 غرف",
    "looking for", "searching for", "need", "want",
    "budget", "apartment", "villa", "studio",
  ];

  const BROKER_SIGNALS = [
    "سمسار", "عقارات", "عندي عقارات", "مطور عقاري",
    "استثمار", "للبيع", "إعلان تجاري",
    "real estate", "broker", "developer",
    "للإيجار", "أجار", "rent",
  ];

  const EGYPT_AREAS = [
    "القاهرة", "الجيزة", "الإسكندرية", "الصعيد",
    "مصر الجديدة", "مدينة نصر", "المعادي", "الزمالك",
    "أكتوبر", "6 أكتوبر", "السادس", "الهرم",
    "الساحل الشمالي", "مرسى مطروح",
    "الشروق", "العبور", "بدر",
    "شبرا", "القليوبية", "بنها",
    "المنطقة 7", "المنطقة 9", "المنطقة 15", "الشريط المميز",
    "المنطقة الصناعية", "المنطقة الحرة",
    "الدمام", "جدة", "الرياض", "دبي", "أبوظبي",
  ];

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let observer = null;
  let processedPosts = new Map(); // Use Map with TTL for bounded memory
  let checkInterval = null;
  const MAX_PROCESSED = 500;
  const POST_TTL = 3600000; // 1 hour

  // ---------------------------------------------------------------------------
  // Selector helpers
  // ---------------------------------------------------------------------------
  function queryFirst(selectors, parent = document) {
    for (const sel of selectors) {
      const el = parent.querySelector(sel);
      if (el) return el;
    }
    return null;
  }

  function queryAllFirst(selectors, parent = document) {
    for (const sel of selectors) {
      const els = parent.querySelectorAll(sel);
      if (els.length > 0) return Array.from(els);
    }
    return [];
  }

  // ---------------------------------------------------------------------------
  // Arabic text normalization (strip diacritics)
  // ---------------------------------------------------------------------------
  function normalizeArabic(text) {
    return text
      .replace(/[\u0610-\u061A]/g, "") // tanwin
      .replace(/[\u064B-\u065F]/g, "") // tashkeel
      .replace(/[\u0670]/g, "") // dagger alif
      .replace(/[\u06D6-\u06DC]/g, "") // Quran marks
      .replace(/\u0640/g, "") // tatweel
      .toLowerCase();
  }

  // ---------------------------------------------------------------------------
  // Post Classification
  // ---------------------------------------------------------------------------
  function classifyPost(text) {
    const lowerText = normalizeArabic(text);

    // Broker first
    if (BROKER_SIGNALS.some((s) => lowerText.includes(normalizeArabic(s)))) {
      return { type: "broker", confidence: 0.9 };
    }

    // Buyer signals
    const matches = BUYER_SIGNALS.filter((s) => lowerText.includes(normalizeArabic(s)));
    if (matches.length > 0) {
      return {
        type: "buyer",
        confidence: Math.min(0.5 + matches.length * 0.15, 0.95),
        signals: matches,
      };
    }

    // Weak signal: area + property keyword
    const areaMatches = EGYPT_AREAS.filter((a) => lowerText.includes(normalizeArabic(a)));
    if (areaMatches.length > 0 && (lowerText.includes("شقة") || lowerText.includes("فيلا"))) {
      return { type: "potential_buyer", confidence: 0.4, areas: areaMatches };
    }

    return { type: "unknown", confidence: 0.1 };
  }

  // ---------------------------------------------------------------------------
  // Extract Post Data
  // ---------------------------------------------------------------------------
  function extractPostData(postElement) {
    try {
      const textEls = queryAllFirst(SELECTORS.postText, postElement);
      let text = textEls.map((el) => el.textContent.trim()).filter(Boolean).join(" ");
      if (!text) return null;

      const authorEl = queryFirst(SELECTORS.postAuthor, postElement);
      const authorName = authorEl ? authorEl.textContent.trim() : "غير معروف";

      const linkEl = queryFirst(SELECTORS.postLink, postElement);
      const postUrl = linkEl ? linkEl.href : "";

      const groupEl = queryFirst(SELECTORS.groupName);
      const groupName = groupEl ? groupEl.textContent.trim() : "Unknown Group";

      // Extract phone numbers from text
      const phones = [];
      const phoneRegex = /(?:\+20|0020|0)?1[0125]\d{8}/g;
      let phoneMatch;
      while ((phoneMatch = phoneRegex.exec(text)) !== null) {
        phones.push(phoneMatch[0]);
      }

      return { text, authorName, postUrl, groupName, phones, timestamp: Date.now() };
    } catch (e) {
      console.error("[CityEstate] Extract failed:", e);
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Dedup (bounded Map with TTL)
  // ---------------------------------------------------------------------------
  function isDuplicate(postId) {
    // Clean expired entries periodically
    if (processedPosts.size > MAX_PROCESSED) {
      const now = Date.now();
      for (const [key, ts] of processedPosts) {
        if (now - ts > POST_TTL) processedPosts.delete(key);
      }
    }
    if (processedPosts.has(postId)) return true;
    processedPosts.set(postId, Date.now());
    return false;
  }

  // ---------------------------------------------------------------------------
  // Process Posts
  // ---------------------------------------------------------------------------
  function processPosts() {
    const posts = queryAllFirst(SELECTORS.postContainer);

    for (const post of posts) {
      // Generate stable post ID
      const linkEl = queryFirst(SELECTORS.postLink, post);
      const postId = linkEl?.href ||
        post.getAttribute("data-ad-rendering-role") ||
        `fb_${btoa(post.textContent.substring(0, 100)).substring(0, 20)}`;

      if (isDuplicate(postId)) continue;

      const postData = extractPostData(post);
      if (!postData) continue;

      const classification = classifyPost(postData.text);

      if (classification.type === "buyer" || classification.type === "potential_buyer") {
        console.log(`[CityEstate] Buyer post: ${postData.authorName}`);

        const intent = extractIntent(postData.text);

        chrome.runtime.sendMessage({
          type: "INCOMING_FACEBOOK",
          payload: {
            groupId: getGroupId(),
            groupName: postData.groupName,
            postId,
            authorName: postData.authorName,
            text: postData.text,
            postUrl: postData.postUrl,
            phones: postData.phones,
            classification,
            intent,
          },
        }).catch((e) => {
          console.warn("[CityEstate] Send failed:", e.message);
        });
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Intent Extraction
  // ---------------------------------------------------------------------------
  function extractIntent(text) {
    const lower = normalizeArabic(text);
    const intent = { area: null, budget: null, bedrooms: null, propertyType: null };

    // Area
    for (const area of EGYPT_AREAS) {
      if (lower.includes(normalizeArabic(area))) { intent.area = area; break; }
    }

    // Budget (improved patterns)
    const budgetPatterns = [
      /(\d[\d,.]*)\s*(مليون|ملايين)/i,
      /(\d+)\s*(ك|k)\b/i,
      /(\d[\d,.]*)\s*(جنيه|ج\.م|egp)/i,
      /(\d[\d,.]*)\s*(الف|ألف)/i,
    ];
    for (const pat of budgetPatterns) {
      const m = lower.match(pat);
      if (m) {
        const num = parseFloat(m[1].replace(/[,.\s]/g, ""));
        if (m[2].includes("مليون") || m[2].includes("ملايين")) intent.budget = num * 1000000;
        else if (m[2].includes("ك") || m[2].includes("k")) intent.budget = num * 1000;
        else if (m[2].includes("الف") || m[2].includes("ألف")) intent.budget = num * 1000;
        else intent.budget = num;
        break;
      }
    }

    // Bedrooms
    if (lower.includes("استوديو")) intent.bedrooms = 0;
    else if (lower.includes("غرفتين") || lower.includes("2 غرف")) intent.bedrooms = 2;
    else if (lower.includes("3 غرف")) intent.bedrooms = 3;
    else if (lower.includes("4 غرف")) intent.bedrooms = 4;
    else if (lower.includes("5 غرف")) intent.bedrooms = 5;

    // Property type
    if (lower.includes("شقة")) intent.propertyType = "apartment";
    else if (lower.includes("فيلا")) intent.propertyType = "villa";
    else if (lower.includes("دوبلكس")) intent.propertyType = "duplex";
    else if (lower.includes("استوديو")) intent.propertyType = "studio";
    else if (lower.includes("محل") || lower.includes("محل تجاري")) intent.propertyType = "commercial";

    return intent;
  }

  function getGroupId() {
    const match = window.location.href.match(/groups\/([^/?#]+)/);
    return match ? match[1] : "unknown";
  }

  // ---------------------------------------------------------------------------
  // Post to Group (React-compatible via InputEvent)
  // ---------------------------------------------------------------------------
  function postToGroup(content) {
    return new Promise((resolve) => {
      const composer = queryFirst(SELECTORS.postComposer);
      if (!composer) { resolve(false); return; }

      composer.focus();

      // Use execCommand (works with React's event system)
      try {
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
        document.execCommand("insertText", false, content);
      } catch (e) {
        // Fallback: InputEvent
        try {
          composer.textContent = content;
          composer.dispatchEvent(new InputEvent("input", {
            inputType: "insertText",
            data: content,
            bubbles: true,
            cancelable: true,
          }));
        } catch (e2) {
          resolve(false);
          return;
        }
      }

      setTimeout(() => {
        const postBtn = queryFirst(SELECTORS.postButton);
        if (postBtn) {
          postBtn.click();
          // Verify post was submitted (check if composer cleared)
          setTimeout(() => {
            const box = queryFirst(SELECTORS.postComposer);
            const posted = box ? box.textContent.trim() === "" : true;
            resolve(posted);
          }, 2000);
        } else {
          resolve(false);
        }
      }, 1000);
    });
  }

  // ---------------------------------------------------------------------------
  // Message Listener
  // ---------------------------------------------------------------------------
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "post_to_group") {
      postToGroup(message.content).then((ok) => sendResponse({ ok }));
      return true;
    }

    if (message.action === "get_posts") {
      const posts = [];
      const els = queryAllFirst(SELECTORS.postContainer);
      for (const post of els) {
        const data = extractPostData(post);
        if (data) {
          data.classification = classifyPost(data.text);
          posts.push(data);
        }
      }
      sendResponse({ posts });
      return false; // synchronous
    }

    return false;
  });

  // ---------------------------------------------------------------------------
  // Initialize
  // ---------------------------------------------------------------------------
  function init() {
    if (!window.location.href.includes("/groups/")) {
      return;
    }

    console.log("[CityEstate] Facebook group monitoring started");

    // Initial scan
    setTimeout(processPosts, 3000);

    // Periodic scan (every 15s, not 10s — reduce load)
    checkInterval = setInterval(processPosts, 15000);

    // DOM observer with debouncing via CityEstateDOMObserver if available
    const feedContainer = queryFirst(SELECTORS.groupFeed);
    if (feedContainer) {
      if (window.CityEstateDOMObserver) {
        window.CityEstateDOMObserver.create(feedContainer, processPosts, {
          childList: true,
          subtree: true,
        });
      } else {
        let timer = null;
        observer = new MutationObserver(() => {
          clearTimeout(timer);
          timer = setTimeout(processPosts, 500);
        });
        observer.observe(feedContainer, { childList: true, subtree: true });
      }
    } else {
      // Retry after 3s if feed not found
      setTimeout(() => {
        const feed = queryFirst(SELECTORS.groupFeed);
        if (feed) {
          let timer = null;
          observer = new MutationObserver(() => {
            clearTimeout(timer);
            timer = setTimeout(processPosts, 500);
          });
          observer.observe(feed, { childList: true, subtree: true });
        }
      }, 3000);
    }
  }

  init();
})();
