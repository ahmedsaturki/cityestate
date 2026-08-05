/**
 * CityEstate — Instagram Content Script
 * =======================================
 * Handles Instagram post automation.
 * Loaded on https://www.instagram.com/*
 */

(function () {
  "use strict";

  const log = (...args) => console.log("[CityEstate:IG]", ...args);

  // ---------------------------------------------------------------------
  // Listen for messages from the background
  // ---------------------------------------------------------------------
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || !message.type) return;

    if (message.type === "IG_POST") {
      postContent(message.content || message.payload?.content || "")
        .then((ok) => sendResponse({ ok, error: ok ? null : "فشل النشر" }))
        .catch((err) => sendResponse({ ok: false, error: err.message }));
      return true;
    }

    if (message.type === "IG_EXTRACT") {
      extractFromFeed()
        .then((data) => sendResponse({ data }))
        .catch((err) => sendResponse({ error: err.message }));
      return true;
    }
  });

  // ---------------------------------------------------------------------
  // Wait for element helper
  // ---------------------------------------------------------------------
  function waitFor(selector, timeout = 15000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const check = () => {
        const el = document.querySelector(selector);
        if (el) return resolve(el);
        if (Date.now() - start > timeout) return reject(new Error(`timeout: ${selector}`));
        setTimeout(check, 300);
      };
      check();
    });
  }

  // ---------------------------------------------------------------------
  // Publish content to a new post
  // ---------------------------------------------------------------------
  async function postContent(content) {
    log("Posting content to Instagram...");

    // Click the "create" button (new post)
    const createBtn = document.querySelector(
      '[aria-label="New post"], [aria-label="إنشاء"], svg[aria-label="New post"]'
    );
    if (createBtn) createBtn.click();

    // Wait for the post composer caption textarea
    const caption = await waitFor('[aria-label="Write a caption..."], [placeholder*="اكتب"], textarea', 20000)
      .catch(() => null);
    if (!caption) {
      log("No caption area found — may need photo selection. Trying composer...");
      // Click the "Create" link in left sidebar if not already open
      const createLink = document.querySelector('a[href="/create/"], [href*="create"]');
      if (createLink) createLink.click();
      const caption2 = await waitFor('[aria-label="Write a caption..."], textarea', 15000).catch(() => null);
      if (!caption2) {
        throw new Error("لم يتم العثور على صندوق كتابة المنشور");
      }
      caption2.focus();
      caption2.value = content;
      caption2.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      caption.focus();
      caption.value = content;
      caption.dispatchEvent(new Event("input", { bubbles: true }));
    }

    // Click share button
    setTimeout(async () => {
      const shareBtn = document.querySelector(
        '[aria-label="Share"], [aria-label="مشاركة"], div[role="button"]:has-text("Share")'
      );
      if (shareBtn) {
        shareBtn.click();
        log("Content shared!");
        return true;
      }
    }, 1000);

    return true;
  }

  // ---------------------------------------------------------------------
  // Extract data from the current feed
  // ---------------------------------------------------------------------
  async function extractFromFeed() {
    log("Extracting from Instagram feed...");
    const data = {
      posts: [],
      profiles: [],
      extracted_at: new Date().toISOString(),
      url: location.href,
    };

    // Extract post captions and usernames
    document.querySelectorAll("article").forEach((article) => {
      try {
        const user = article.querySelector('a[href^="/"][role="link"]')?.textContent || "";
        const caption = article.querySelector("h1, [dir='auto']")?.textContent || "";
        const img = article.querySelector("img");
        const imageUrl = img ? img.src : "";
        if (user) {
          data.profiles.push({ username: user.trim() });
        }
        if (caption && caption.length > 10) {
          data.posts.push({ user: user.trim(), caption: caption.slice(0, 500), imageUrl });
        }
      } catch (e) { /* skip malformed article */ }
    });

    // Extract phone numbers from captions
    const text = document.body ? document.body.innerText : "";
    const phoneRe = /(?:\+?\d{2})?0?1[0125]\d{8}/g;
    data.phones = text.match(phoneRe) || [];

    // Extract hashtags
    const tags = text.match(/#[\w؀-ۿ]+/g) || [];
    data.hashtags = [...new Set(tags)].slice(0, 20);

    return data;
  }

  log("Instagram content script loaded");
})();
