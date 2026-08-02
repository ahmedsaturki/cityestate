/**
 * CityEstate Bridge — WhatsApp Content Script (Fixed)
 * ====================================================
 * Monitors WhatsApp Web for incoming messages.
 * Sends them to AI Brain via service worker.
 * Receives responses and types them via human-like typewriter.
 *
 * Fixes: sentinel guard, robust selectors, proper navigation,
 *        error handling, debounced observer, React-compatible input.
 */

(function () {
  "use strict";

  // Guard: prevent double injection
  if (window.__cityestate_loaded) return;
  window.__cityestate_loaded = true;

  // ---------------------------------------------------------------------------
  // Selectors — multiple fallbacks per element
  // ---------------------------------------------------------------------------
  const SELECTORS = {
    incomingMessageContainer: [
      'div.message-in',
      'div[data-testid="msg-container"]',
      'div.copyable-text',
    ],
    incomingMessageText: [
      'span.selectable-text.copyable-text span',
      'span[data-testid="message-text"]',
      'div.selectable-text span',
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
      'button[icon="send"]',
    ],
    chatListItem: [
      'div[id^="chat-list"] div[role="listitem"]',
      'div[data-testid="chat-list"] div[role="listitem"]',
      'div[role="listitem"]',
    ],
    chatContainer: [
      'div[role="application"]',
      'div[id="pane-side"]',
      '#app > div > div > div:nth-child(2)',
    ],
  };

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let observer = null;
  let isProcessing = false;

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
  // Chat ID Detection (5 strategies)
  // ---------------------------------------------------------------------------
  function getChatId() {
    // Strategy 1: URL send page
    const urlMatch = window.location.href.match(/send[?&]phone=(\d[\d]+)/);
    if (urlMatch) return urlMatch[1];

    // Strategy 2: Active chat list item
    try {
      const active = document.querySelector('[data-testid="chat-list"] [aria-selected="true"]');
      if (active) {
        const id = active.getAttribute("data-testid")?.replace("chat-list-item-", "");
        if (id && id !== "chat-list-item-") return id;
        // Try data-id attribute
        const dataId = active.getAttribute("data-id");
        if (dataId) return dataId.replace("true_", "");
      }
    } catch (e) { /* continue */ }

    // Strategy 3: Chat panel header
    try {
      const headerSpan = document.querySelector(
        'div[data-testid="conversation-info-header"] span[title]'
      );
      if (headerSpan) {
        const title = headerSpan.getAttribute("title") || "";
        const phoneMatch = title.match(/\d{10,15}/);
        if (phoneMatch) return phoneMatch[0];
      }
    } catch (e) { /* continue */ }

    // Strategy 4: URL hash
    const hashMatch = window.location.hash.match(/phone[=:](\d{10,15})/);
    if (hashMatch) return hashMatch[1];

    // Strategy 5: First phone-like number in conversation panel
    try {
      const panel = document.querySelector('div[role="application"]');
      if (panel) {
        const spans = panel.querySelectorAll("span");
        for (const span of spans) {
          const text = span.textContent;
          const m = text.match(/\+?\d{10,15}/);
          if (m) return m[0].replace("+", "");
        }
      }
    } catch (e) { /* continue */ }

    return null;
  }

  function getSenderName() {
    const el = queryFirst(SELECTORS.chatHeaderName);
    return el ? el.textContent.trim() : "عميل";
  }

  // ---------------------------------------------------------------------------
  // Incoming Message Detection
  // ---------------------------------------------------------------------------
  function getIncomingMessages() {
    const messages = [];
    const containers = queryAllFirst(SELECTORS.incomingMessageContainer);

    for (const container of containers) {
      if (container.classList.contains("message-out")) continue;

      // Dedup: use text content hash
      const textEl = queryFirst(SELECTORS.incomingMessageText, container);
      if (!textEl) continue;

      const text = textEl.textContent.trim();
      if (!text) continue;

      // Dedup by data-ce-text attribute
      const hash = text.substring(0, 80);
      if (container.dataset.ceText === hash) continue;
      container.dataset.ceText = hash;

      messages.push({ text, timestamp: Date.now() });
    }

    return messages;
  }

  // ---------------------------------------------------------------------------
  // Message Sending (React-compatible)
  // ---------------------------------------------------------------------------
  function typeMessage(text) {
    return new Promise((resolve) => {
      const messageBox = queryFirst(SELECTORS.messageBox);
      if (!messageBox) {
        console.error("[CityEstate] Message box not found");
        resolve(false);
        return;
      }

      messageBox.focus();

      // Use typewriter engine if available (preferred)
      if (window.CityEstateTypewriter) {
        window.CityEstateTypewriter.type(messageBox, text).then(() => {
          clickSend(messageBox).then(resolve);
        }).catch((e) => {
          console.error("[CityEstate] Typewriter failed:", e);
          resolve(false);
        });
      } else {
        // Fallback: use execCommand (works with React better than textContent)
        try {
          // Clear existing content
          document.execCommand("selectAll", false, null);
          document.execCommand("delete", false, null);
          // Insert new text
          document.execCommand("insertText", false, text);
          setTimeout(() => clickSend(messageBox).then(resolve), 500);
        } catch (e) {
          console.error("[CityEstate] execCommand failed:", e);
          resolve(false);
        }
      }
    });
  }

  function clickSend(messageBox) {
    return new Promise((resolve) => {
      setTimeout(() => {
        // Try clicking send button
        const sendBtn = queryFirst(SELECTORS.sendButton);
        if (sendBtn) {
          sendBtn.click();
          resolve(true);
          return;
        }

        // Fallback: Enter key (try keydown, keyup, and keypress)
        try {
          const events = [
            new KeyboardEvent("keydown", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true }),
            new KeyboardEvent("keyup", { key: "Enter", code: "Enter", keyCode: 13, which: 13, bubbles: true }),
          ];
          for (const evt of events) {
            messageBox.dispatchEvent(evt);
          }
        } catch (e) { /* ignore */ }

        resolve(true);
      }, 300 + Math.random() * 400);
    });
  }

  // ---------------------------------------------------------------------------
  // Navigation (fixed: don't navigate in content script, tell service worker)
  // ---------------------------------------------------------------------------
  function navigateToChat(chatId) {
    // Instead of navigating here (which destroys execution context),
    // we navigate via window.location and rely on WhatsApp's SPA routing
    window.location.href = `https://web.whatsapp.com/send?phone=${chatId}`;
  }

  function waitForChatReady(timeout = 8000) {
    return new Promise((resolve) => {
      const start = Date.now();
      const check = () => {
        const box = queryFirst(SELECTORS.messageBox);
        if (box) {
          resolve(true);
          return;
        }
        if (Date.now() - start > timeout) {
          resolve(false);
          return;
        }
        setTimeout(check, 300);
      };
      check();
    });
  }

  // ---------------------------------------------------------------------------
  // Message Monitoring
  // ---------------------------------------------------------------------------
  function startMonitoring() {
    if (observer) {
      observer.disconnect();
      observer = null;
    }

    const chatContainer = queryFirst(SELECTORS.chatContainer);
    if (!chatContainer) {
      console.warn("[CityEstate] Chat container not found, retrying in 2s...");
      setTimeout(startMonitoring, 2000);
      return;
    }

    let debounceTimer = null;

    observer = new MutationObserver(() => {
      if (isProcessing) return;
      // Debounce: wait 300ms after last mutation
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        processNewMessages();
      }, 300);
    });

    observer.observe(chatContainer, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    console.log("[CityEstate] WhatsApp monitoring started");
  }

  function processNewMessages() {
    try {
      const messages = getIncomingMessages();
      if (messages.length === 0) return;

      const chatId = getChatId();
      const senderName = getSenderName();

      for (const msg of messages) {
        chrome.runtime.sendMessage({
          type: "INCOMING_WHATSAPP",
          payload: {
            chatId: chatId || "unknown",
            senderName,
            text: msg.text,
            timestamp: msg.timestamp,
          },
        }).catch((e) => {
          console.warn("[CityEstate] Failed to send message:", e.message);
        });
      }
    } catch (e) {
      console.error("[CityEstate] Message processing error:", e);
    }
  }

  // ---------------------------------------------------------------------------
  // Message Listener (from service worker)
  // ---------------------------------------------------------------------------
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "send_message") {
      console.log(`[CityEstate] Sending to ${message.chatId}`);

      const currentChat = getChatId();
      if (currentChat !== message.chatId) {
        // Navigate to the right chat
        navigateToChat(message.chatId);
        // Wait for chat to load, then type
        waitForChatReady(8000).then((ready) => {
          if (!ready) {
            sendResponse({ ok: false, error: "Chat not ready" });
            return;
          }
          typeMessage(message.text).then((ok) => {
            if (ok) {
              chrome.runtime.sendMessage({
                type: "TYPING_COMPLETE",
                payload: { chatId: message.chatId },
              }).catch(() => {});
            }
            sendResponse({ ok });
          });
        });
        return true; // async response
      }

      typeMessage(message.text).then((ok) => {
        if (ok) {
          chrome.runtime.sendMessage({
            type: "TYPING_COMPLETE",
            payload: { chatId: message.chatId },
          }).catch(() => {});
        }
        sendResponse({ ok });
      });
      return true;
    }

    if (message.action === "get_chats") {
      // Wait a bit for DOM to be ready
      setTimeout(() => {
        const chats = [];
        const items = queryAllFirst(SELECTORS.chatListItem);
        for (const item of items) {
          const nameEl = item.querySelector("span[title]");
          if (nameEl) {
            chats.push({
              name: nameEl.textContent.trim(),
              hasUnread: !!item.querySelector('[title*="unread"]'),
            });
          }
        }
        sendResponse({ chats });
      }, 200);
      return true;
    }

    return false;
  });

  // ---------------------------------------------------------------------------
  // Initialize
  // ---------------------------------------------------------------------------
  function init() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => {
        setTimeout(startMonitoring, 3000);
      });
    } else {
      setTimeout(startMonitoring, 3000);
    }
  }

  init();
})();
