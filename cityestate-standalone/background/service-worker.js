/**
 * CityEstate Standalone — Service Worker
 * ========================================
 * MV3 background script. Runs entirely locally — NO WebSocket, NO backend.
 * Handles:
 * - Message routing between content scripts
 * - Local lead scoring (delegates to content scripts which have the scorer)
 * - Chrome storage for leads, notes, stats
 * - Badge updates
 * - Notifications for hot leads
 */

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let messageCounter = { sent: 0, received: 0 };

// ---------------------------------------------------------------------------
// Badge
// ---------------------------------------------------------------------------
function updateBadge(count) {
  const text = count > 0 ? String(count) : "";
  chrome.action.setBadgeBackgroundColor({ color: "#25D366" });
  chrome.action.setBadgeText({ text });
}

// ---------------------------------------------------------------------------
// Store lead locally
// ---------------------------------------------------------------------------
async function storeLead(leadData) {
  try {
    const stored = await chrome.storage.local.get("leads");
    const leads = stored.leads || [];

    // Dedup
    const hash = `${leadData.chatId || ""}_${(leadData.text || "").substring(0, 50)}`;
    if (leads.some((l) => l._hash === hash)) return;

    leadData._hash = hash;
    leadData._ts = Date.now();
    leads.unshift(leadData);

    // Trim
    if (leads.length > 500) leads.length = 500;

    await chrome.storage.local.set({ leads });

    // Update stats
    const statsStored = await chrome.storage.local.get("stats");
    const stats = statsStored.stats || { totalLeads: 0, leadsByTier: {}, messagesProcessed: 0, autoReplies: 0 };
    stats.totalLeads = leads.length;
    stats.leadsByTier[leadData.tier || "unknown"] = (stats.leadsByTier[leadData.tier || "unknown"] || 0) + 1;
    stats.lastActivity = Date.now();
    await chrome.storage.local.set({ stats });

    // Update badge
    updateBadge(leads.length);

    // Notify popup
    chrome.runtime.sendMessage({ type: "LEAD_UPDATE", payload: leadData }).catch(() => {});

    // Hot lead notification
    if (leadData.score >= 80) {
      try {
        await chrome.notifications.create(`hot_${Date.now()}`, {
          type: "basic",
          iconUrl: "icons/icon128.png",
          title: "عميل ساخن! — CityEstate",
          message: `${leadData.senderName || "عميل"} — درجة ${leadData.score}/100 (${leadData.tier})`,
        });
      } catch (e) { /* best effort */ }
    }
  } catch (e) {
    console.error("[CityEstate] storeLead failed:", e);
  }
}

// ---------------------------------------------------------------------------
// Store note
// ---------------------------------------------------------------------------
async function storeNote(note) {
  try {
    const stored = await chrome.storage.local.get("notes");
    const notes = stored.notes || [];
    note._ts = Date.now();
    note._id = `note_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    notes.unshift(note);
    if (notes.length > 200) notes.length = 200;
    await chrome.storage.local.set({ notes });
    return note._id;
  } catch (e) {
    console.error("[CityEstate] storeNote failed:", e);
  }
}

// ---------------------------------------------------------------------------
// Route message to content script
// ---------------------------------------------------------------------------
async function routeToContentScript(platform, message) {
  try {
    const pattern = platform === "whatsapp"
      ? "https://web.whatsapp.com/*"
      : "https://www.facebook.com/*";

    const tabs = await chrome.tabs.query({ url: pattern });
    if (tabs.length === 0) return;

    for (const tab of tabs) {
      try {
        await chrome.tabs.sendMessage(tab.id, message);
      } catch (e) {
        // Tab not reachable
      }
    }
  } catch (e) {
    console.error("[CityEstate] Route failed:", e);
  }
}

// ---------------------------------------------------------------------------
// Message Listener
// ---------------------------------------------------------------------------
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const type = message.type;

  // --- Status request from popup ---
  if (type === "GET_STATUS") {
    chrome.storage.local.get(["stats", "leads"]).then((data) => {
      const stats = data.stats || { totalLeads: 0, leadsByTier: {}, messagesProcessed: 0 };
      const leads = data.leads || [];
      const lastLead = leads.length > 0 ? leads[0] : null;
      sendResponse({
        mode: "standalone",
        stats,
        lastLead,
        messagesProcessed: stats.messagesProcessed || 0,
      });
    });
    return true;
  }

  // --- Incoming from WhatsApp content script ---
  if (type === "INCOMING_WHATSAPP") {
    messageCounter.received++;
    // Forward to WhatsApp tab for local scoring
    routeToContentScript("whatsapp", {
      action: "score_and_reply",
      payload: message.payload,
    });
    sendResponse({ ok: true });
    return false;
  }

  // --- Incoming from Facebook content script ---
  if (type === "INCOMING_FACEBOOK") {
    messageCounter.received++;
    // Score locally in service worker
    const payload = message.payload;
    const score = scoreLocal(payload.text, payload.source || "facebook");
    const leadData = {
      ...payload,
      score: score.score,
      tier: score.tier,
      breakdown: score.breakdown,
      source: "facebook",
    };
    storeLead(leadData);
    sendResponse({ ok: true });
    return false;
  }

  // --- Lead scored by content script ---
  if (type === "LEAD_SCORED") {
    storeLead(message.payload);
    sendResponse({ ok: true });
    return false;
  }

  // --- Send message to WhatsApp ---
  if (type === "SEND_WHATSAPP") {
    routeToContentScript("whatsapp", {
      action: "send_message",
      chatId: message.chatId,
      text: message.text,
    });
    messageCounter.sent++;
    sendResponse({ ok: true });
    return false;
  }

  // --- Quick note ---
  if (type === "ADD_NOTE") {
    storeNote(message.note).then((id) => sendResponse({ ok: true, id }));
    return true;
  }

  // --- Get notes ---
  if (type === "GET_NOTES") {
    chrome.storage.local.get("notes").then((data) => {
      sendResponse({ notes: data.notes || [] });
    });
    return true;
  }

  // --- Delete note ---
  if (type === "DELETE_NOTE") {
    chrome.storage.local.get("notes").then((data) => {
      const notes = (data.notes || []).filter((n) => n._id !== message.id);
      chrome.storage.local.set({ notes }).then(() => sendResponse({ ok: true }));
    });
    return true;
  }

  // --- Update settings ---
  if (type === "UPDATE_SETTINGS") {
    chrome.storage.local.get("settings").then((data) => {
      const settings = { ...(data.settings || {}), ...message.settings };
      chrome.storage.local.set({ settings }).then(() => sendResponse({ ok: true }));
    });
    return true;
  }

  // --- Get settings ---
  if (type === "GET_SETTINGS") {
    chrome.storage.local.get("settings").then((data) => {
      sendResponse({
        settings: data.settings || {
          autoReplyEnabled: true,
          showNotifications: true,
          scoreThreshold: 40,
        },
      });
    });
    return true;
  }

  return false;
});

// ---------------------------------------------------------------------------
// Simple local scoring (mirror of lead-scorer.js for service worker context)
// ---------------------------------------------------------------------------
function scoreLocal(text, source) {
  if (!text) return { score: 0, tier: "rejected", breakdown: {} };

  const lower = text
    .replace(/[\u0610-\u061A]/g, "")
    .replace(/[\u064B-\u065F]/g, "")
    .replace(/\u0640/g, "")
    .toLowerCase();

  // Broker check
  const brokerKw = ["سمسار", "عقارات", "للبيع", "broker", "developer", "rent", "أجار"];
  if (brokerKw.some((kw) => lower.includes(kw))) {
    return { score: 0, tier: "rejected", breakdown: { broker: -30 } };
  }

  let score = 0;
  const breakdown = {};

  // Property type
  if (/مصنع|مصانع|صناعي/.test(lower)) { breakdown.property_type = 20; score += 20; }
  else if (/محل|تجاري/.test(lower)) { breakdown.property_type = 20; score += 20; }
  else if (/فيلا|كمبوند/.test(lower)) { breakdown.property_type = 15; score += 15; }
  else if (/شقة/.test(lower)) { breakdown.property_type = 8; score += 8; }

  // Budget
  const budgetMatch = lower.match(/(\d[\d,.]*)\s*(مليون|ك|k|جنيه)/);
  if (budgetMatch) {
    const num = parseFloat(budgetMatch[1].replace(/[,.\s]/g, ""));
    let budget = num;
    if (budgetMatch[2].includes("مليون")) budget = num * 1000000;
    else if (budgetMatch[2].includes("ك") || budgetMatch[2].includes("k")) budget = num * 1000;
    if (budget >= 3000000) { breakdown.budget = 35; score += 35; }
    else if (budget >= 1500000) { breakdown.budget = 25; score += 25; }
    else if (budget >= 500000) { breakdown.budget = 15; score += 15; }
    else { breakdown.budget = 8; score += 8; }
  }

  // Timeline
  if (/عاجل|فورا|urgent/.test(lower)) { breakdown.timeline = 10; score += 10; }

  // Area Sadat
  if (/سادات|منطقة 7|منطقة 9|منطقة 15|الشريط/.test(lower)) { breakdown.area = 10; score += 10; }

  // Seriousness
  if (/عايز|أبحث|بدي|looking|want/.test(lower)) { breakdown.seriousness = 10; score += 10; }

  // WhatsApp origin
  if (source === "whatsapp") { breakdown.origin = 10; score += 10; }

  // Phone
  if (/\d{10,}/.test(text)) { breakdown.contact = 5; score += 5; }

  score = Math.min(score, 100);

  let tier;
  if (score >= 80) tier = "platinum";
  else if (score >= 60) tier = "gold";
  else if (score >= 40) tier = "silver";
  else tier = "rejected";

  return { score, tier, breakdown };
}

// ---------------------------------------------------------------------------
// Initialize
// ---------------------------------------------------------------------------
chrome.runtime.onInstalled.addListener(() => {
  console.log("[CityEstate] Standalone extension installed");
  chrome.storage.local.get("stats").then((data) => {
    if (!data.stats) {
      chrome.storage.local.set({
        stats: { totalLeads: 0, leadsByTier: {}, messagesProcessed: 0, autoReplies: 0 },
      });
    }
  });
});
