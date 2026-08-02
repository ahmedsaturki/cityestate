/**
 * CityEstate Standalone — Facebook Content Script
 * ==================================================
 * Monitors Facebook Groups for buyer-intent posts.
 * Scores leads locally using CityEstateLeadScorer.
 * NO backend needed — everything runs in the browser.
 */

(function () {
  "use strict";

  if (window.__cityestate_standalone_fb) return;
  window.__cityestate_standalone_fb = true;

  // ---------------------------------------------------------------------------
  // Selectors
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
    ],
    postLink: [
      'a[href*="/posts/"]',
      'a[href*="/permalink/"]',
      'a[href*="/story.php"]',
    ],
    groupName: [
      'h1 span',
      'a[href*="/groups/"] span',
    ],
  };

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let observer = null;
  let processedPosts = new Map();
  const MAX_PROCESSED = 500;
  const POST_TTL = 3600000;

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function q(selectors, parent = document) {
    for (const s of selectors) {
      const el = parent.querySelector(s);
      if (el) return el;
    }
    return null;
  }

  function qAll(selectors, parent = document) {
    for (const s of selectors) {
      const els = parent.querySelectorAll(s);
      if (els.length > 0) return Array.from(els);
    }
    return [];
  }

  function normalize(text) {
    return text
      .replace(/[\u0610-\u061A]/g, "")
      .replace(/[\u064B-\u065F]/g, "")
      .replace(/\u0640/g, "")
      .toLowerCase();
  }

  // ---------------------------------------------------------------------------
  // Buyer/broker classification
  // ---------------------------------------------------------------------------
  const BUYER_SIGNALS = [
    "مطلوب", "مطلوب شقة", "مطلوب عقار", "مطلوب فيلا",
    "عايز", "أبحث", "أدور", "بدي", "محتاج",
    "حد يساعدني", "لو في حد",
    "ميزانية", "ميزانيتي", "أقدر أدفع",
    "استوديو", "غرفتين", "3 غرف",
    "looking for", "searching for", "need", "want", "budget",
  ];

  const BROKER_SIGNALS = [
    "سمسار", "عقارات", "عندي عقارات", "مطور عقاري",
    "للبيع", "إعلان تجاري", "للإيجار", "أجار",
    "real estate", "broker", "developer", "rent",
  ];

  function classifyPost(text) {
    const lower = normalize(text);
    if (BROKER_SIGNALS.some((s) => lower.includes(normalize(s)))) {
      return { type: "broker", confidence: 0.9 };
    }
    const matches = BUYER_SIGNALS.filter((s) => lower.includes(normalize(s)));
    if (matches.length > 0) {
      return { type: "buyer", confidence: Math.min(0.5 + matches.length * 0.15, 0.95), signals: matches };
    }
    return { type: "unknown", confidence: 0.1 };
  }

  // ---------------------------------------------------------------------------
  // Extract post data
  // ---------------------------------------------------------------------------
  function extractPostData(postElement) {
    try {
      const textEls = qAll(SELECTORS.postText, postElement);
      let text = textEls.map((el) => el.textContent.trim()).filter(Boolean).join(" ");
      if (!text) return null;

      const authorEl = q(SELECTORS.postAuthor, postElement);
      const authorName = authorEl ? authorEl.textContent.trim() : "غير معروف";

      const linkEl = q(SELECTORS.postLink, postElement);
      const postUrl = linkEl ? linkEl.href : "";

      const groupEl = q(SELECTORS.groupName);
      const groupName = groupEl ? groupEl.textContent.trim() : "Unknown Group";

      // Extract phones
      const phones = [];
      const phoneRegex = /(?:\+20|0020|0)?1[0125]\d{8}/g;
      let phoneMatch;
      while ((phoneMatch = phoneRegex.exec(text)) !== null) {
        phones.push(phoneMatch[0]);
      }

      return { text, authorName, postUrl, groupName, phones, timestamp: Date.now() };
    } catch (e) {
      return null;
    }
  }

  // ---------------------------------------------------------------------------
  // Dedup
  // ---------------------------------------------------------------------------
  function isDuplicate(postId) {
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
  // Process posts
  // ---------------------------------------------------------------------------
  function processPosts() {
    const posts = qAll(SELECTORS.postContainer);

    for (const post of posts) {
      const linkEl = q(SELECTORS.postLink, post);
      const postId = linkEl?.href ||
        `fb_${btoa(post.textContent.substring(0, 100)).substring(0, 20)}`;

      if (isDuplicate(postId)) continue;

      const postData = extractPostData(post);
      if (!postData) continue;

      const classification = classifyPost(postData.text);

      if (classification.type === "buyer") {
        console.log(`[CityEstate] FB buyer post: ${postData.authorName}`);

        // Score locally using lead-scorer
        let scoreResult = { score: 0, tier: "rejected" };
        if (window.CityEstateLeadScorer) {
          scoreResult = window.CityEstateLeadScorer.scoreLead({
            text: postData.text,
            senderName: postData.authorName,
            source: "facebook",
          });
        }

        // Store via service worker
        chrome.runtime.sendMessage({
          type: "INCOMING_FACEBOOK",
          payload: {
            chatId: postId,
            senderName: postData.authorName,
            text: postData.text,
            postUrl: postData.postUrl,
            groupName: postData.groupName,
            phones: postData.phones,
            score: scoreResult.score,
            tier: scoreResult.tier,
            breakdown: scoreResult.breakdown,
            propertyType: scoreResult.propertyType,
            budget: scoreResult.budget,
            area: scoreResult.area,
            timeline: scoreResult.timeline,
            source: "facebook",
          },
        }).catch(() => {});
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  function init() {
    if (!window.location.href.includes("/groups/")) return;

    console.log("[CityEstate] Facebook standalone monitoring started");

    setTimeout(processPosts, 3000);

    // Periodic scan
    setInterval(processPosts, 15000);

    // DOM observer
    const feed = q(SELECTORS.groupFeed);
    if (feed) {
      let timer = null;
      observer = new MutationObserver(() => {
        clearTimeout(timer);
        timer = setTimeout(processPosts, 500);
      });
      observer.observe(feed, { childList: true, subtree: true });
    }
  }

  init();
})();
