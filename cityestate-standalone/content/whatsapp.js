/**
 * CityEstate Standalone — WhatsApp Content Script
 * =================================================
 * Monitors WhatsApp Web for incoming messages.
 * Scores leads locally using CityEstateLeadScorer.
 * Auto-replies using CityEstateAutoReply.
 * NO backend needed — everything runs in the browser.
 */

(function () {
  "use strict";

  if (window.__cityestate_standalone) return;
  window.__cityestate_standalone = true;

  // ---------------------------------------------------------------------------
  // Selectors
  // ---------------------------------------------------------------------------
  const SELECTORS = {
    incomingMsg: [
      'div.message-in',
      'div[data-testid="msg-container"]',
    ],
    incomingText: [
      'span.selectable-text.copyable-text span',
      'span[data-testid="message-text"]',
    ],
    chatHeaderName: [
      'span[title]:not([data-testid])',
      'div[data-testid="conversation-info-header"] span[title]',
      'header span[title]',
    ],
    messageBox: [
      'div[contenteditable="true"][data-tab="10"]',
      'div[contenteditable="true"][role="textbox"]',
      'footer div[contenteditable="true"]',
    ],
    sendButton: [
      'button[data-testid="send"]',
      'span[data-testid="send"]',
      'button[aria-label="Send"]',
    ],
    chatContainer: [
      'div[role="application"]',
      'div[id="pane-side"]',
    ],
  };

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let observer = null;
  let isProcessing = false;

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

  // ---------------------------------------------------------------------------
  // Chat detection
  // ---------------------------------------------------------------------------
  function getChatId() {
    const m = window.location.href.match(/send[?&]phone=(\d[\d]+)/);
    if (m) return m[1];
    try {
      const active = document.querySelector('[data-testid="chat-list"] [aria-selected="true"]');
      if (active) {
        const id = active.getAttribute("data-id");
        if (id) return id.replace("true_", "");
      }
    } catch (e) {}
    return null;
  }

  function getSenderName() {
    const el = q(SELECTORS.chatHeaderName);
    return el ? el.textContent.trim() : "عميل";
  }

  // ---------------------------------------------------------------------------
  // Message detection
  // ---------------------------------------------------------------------------
  function getIncomingMessages() {
    const messages = [];
    const containers = qAll(SELECTORS.incomingMsg);
    for (const c of containers) {
      if (c.classList.contains("message-out")) continue;
      const textEl = q(SELECTORS.incomingText, c);
      if (!textEl) continue;
      const text = textEl.textContent.trim();
      if (!text) continue;
      const hash = text.substring(0, 80);
      if (c.dataset.ceStandalone === hash) continue;
      c.dataset.ceStandalone = hash;
      messages.push({ text, ts: Date.now() });
    }
    return messages;
  }

  // ---------------------------------------------------------------------------
  // Scoring + Auto-reply
  // ---------------------------------------------------------------------------
  function processMessage(text, senderName, chatId) {
    if (!window.CityEstateLeadScorer) {
      console.warn("[CityEstate] LeadScorer not loaded");
      return;
    }

    const scorer = window.CityEstateLeadScorer;
    const result = scorer.scoreLead({
      text,
      senderName,
      source: "whatsapp",
    });

    console.log(`[CityEstate] Score: ${result.score}/${result.tier}`, result.breakdown);

    // Store lead via service worker
    chrome.runtime.sendMessage({
      type: "LEAD_SCORED",
      payload: {
        chatId,
        senderName,
        text,
        score: result.score,
        tier: result.tier,
        breakdown: result.breakdown,
        reasons: result.reasons,
        propertyType: result.propertyType,
        budget: result.budget,
        area: result.area,
        timeline: result.timeline,
        phone: result.phone,
        source: "whatsapp",
      },
    }).catch(() => {});

    // Auto-reply if enabled and lead is qualified
    if (result.tier !== "rejected" && window.CityEstateAutoReply) {
      const settings = getAutoReplySettings();
      if (settings.autoReplyEnabled && result.score >= (settings.scoreThreshold || 40)) {
        const reply = window.CityEstateAutoReply.generateReply(
          result,
          {
            propertyType: result.propertyType,
            budget: result.budget,
            area: result.area,
            timeline: result.timeline,
          },
          senderName
        );
        if (reply) {
          console.log("[CityEstate] Auto-reply prepared (not sent — manual review recommended)");
          // Store the suggested reply
          chrome.runtime.sendMessage({
            type: "LEAD_SCORED",
            payload: {
              chatId,
              senderName,
              text: `[SUGGESTED REPLY]\n${reply}`,
              score: result.score,
              tier: result.tier,
              source: "whatsapp_suggestion",
            },
          }).catch(() => {});
        }
      }
    }
  }

  function getAutoReplySettings() {
    // Read from storage synchronously via a trick
    let settings = { autoReplyEnabled: true, scoreThreshold: 40 };
    chrome.storage.local.get("settings").then((data) => {
      if (data.settings) settings = data.settings;
    }).catch(() => {});
    return settings;
  }

  // ---------------------------------------------------------------------------
  // Message sending
  // ---------------------------------------------------------------------------
  function typeMessage(text) {
    return new Promise((resolve) => {
      const box = q(SELECTORS.messageBox);
      if (!box) { resolve(false); return; }
      box.focus();
      try {
        document.execCommand("selectAll", false, null);
        document.execCommand("delete", false, null);
        document.execCommand("insertText", false, text);
        setTimeout(() => {
          const btn = q(SELECTORS.sendButton);
          if (btn) { btn.click(); resolve(true); }
          else {
            box.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", keyCode: 13, bubbles: true }));
            resolve(true);
          }
        }, 500);
      } catch (e) {
        resolve(false);
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Monitoring
  // ---------------------------------------------------------------------------
  function startMonitoring() {
    if (observer) observer.disconnect();

    const container = q(SELECTORS.chatContainer);
    if (!container) {
      setTimeout(startMonitoring, 2000);
      return;
    }

    let timer = null;
    observer = new MutationObserver(() => {
      if (isProcessing) return;
      clearTimeout(timer);
      timer = setTimeout(processNewMessages, 300);
    });

    observer.observe(container, { childList: true, subtree: true, characterData: true });
    console.log("[CityEstate] WhatsApp standalone monitoring started");
  }

  function processNewMessages() {
    try {
      const messages = getIncomingMessages();
      if (messages.length === 0) return;

      const chatId = getChatId();
      const senderName = getSenderName();

      for (const msg of messages) {
        processMessage(msg.text, senderName, chatId);
      }
    } catch (e) {
      console.error("[CityEstate] Processing error:", e);
    }
  }

  // ---------------------------------------------------------------------------
  // Message listener (from popup or service worker)
  // ---------------------------------------------------------------------------
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "send_message") {
      typeMessage(message.text).then((ok) => sendResponse({ ok }));
      return true;
    }

    if (message.action === "score_and_reply") {
      const p = message.payload;
      processMessage(p.text, p.senderName, p.chatId);
      sendResponse({ ok: true });
      return false;
    }

    return false;
  });

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  function init() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => setTimeout(startMonitoring, 3000));
    } else {
      setTimeout(startMonitoring, 3000);
    }
  }

  init();
})();
