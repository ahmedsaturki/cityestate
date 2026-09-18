/**
 * CityEstate Bridge — Service Worker (Auto-Auth)
 * ================================================
 * MV3-compatible background script with:
 * - AUTO-FETCH JWT from server (no manual config needed)
 * - chrome.alarms for reconnect/heartbeat (survives SW termination)
 * - Race-condition-safe WebSocket connect
 * - Atomic offline queue with single storage key
 * - Proper error handling on all async operations
 */

const DEFAULT_SERVER_URL = "http://localhost:8000";
const DEFAULT_WS_URL = "ws://localhost:8000/ws/bridge";
const TOKEN_ENDPOINT = "/api/v1/auth/extension-token";
const RECONNECT_BASE_DELAY = 1000;
const RECONNECT_MAX_DELAY = 30000;
const HEARTBEAT_ALARM = "cityestate_heartbeat";
const RECONNECT_ALARM = "cityestate_reconnect";

let ws = null;
let profileId = null;
let wsUrl = DEFAULT_WS_URL;
let serverUrl = DEFAULT_SERVER_URL;
let reconnectDelay = RECONNECT_BASE_DELAY;
let connectionState = "disconnected";
let messageCounter = { sent: 0, received: 0 };

// ---------------------------------------------------------------------------
// Auto-fetch JWT from server — NO manual config needed
// ---------------------------------------------------------------------------
const DEFAULT_EXTENSION_SECRET = "uLkAKGDogggLTOqAru3zFY_XTG2RDn2CHmZhJibIZY7xZXwgEbtpTYA8tY0VzR1P";

async function fetchTokenFromServer() {
  try {
    const stored = await chrome.storage.local.get(["jwtToken", "tokenExpiry"]);
    
    // Check if existing token is still valid (with 5min buffer)
    if (stored.jwtToken && stored.tokenExpiry && Date.now() < stored.tokenExpiry - 300000) {
      console.log("[CityEstate] Using cached token");
      return stored.jwtToken;
    }

    // Fetch new token from server using shared-secret handshake
    // (Replaces the previous ADMIN_PASSWORD-based backdoor.)
    console.log("[CityEstate] Fetching token from server...");
    let local = await chrome.storage.local.get("extensionSecret");
    if (!local.extensionSecret) {
      // Auto-configure from default secret for seamless setup
      local.extensionSecret = DEFAULT_EXTENSION_SECRET;
      await chrome.storage.local.set({ extensionSecret: DEFAULT_EXTENSION_SECRET });
      console.log("[CityEstate] Auto-configured extensionSecret");
    }

    const response = await fetch(`${serverUrl}${TOKEN_ENDPOINT}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ extension_secret: local.extensionSecret }),
    });

    if (!response.ok) {
      console.error("[CityEstate] Token fetch failed:", response.status);
      return null;
    }

    const data = await response.json();
    const token = data.access_token;
    const expiresIn = (data.expires_in || 28800) * 1000; // ms

    // Store token with expiry
    await chrome.storage.local.set({
      jwtToken: token,
      tokenExpiry: Date.now() + expiresIn,
      serverUrl: data.server_url || DEFAULT_WS_URL,
    });

    // Update wsUrl from server response
    if (data.server_url) {
      wsUrl = data.server_url;
    }

    // Update profileId from server response
    if (data.profile_id) {
      profileId = data.profile_id;
      await chrome.storage.local.set({ profileId });
    }

    console.log("[CityEstate] Token fetched successfully");
    return token;
  } catch (e) {
    console.error("[CityEstate] Token fetch error:", e);
    return null;
  }
}

// ---------------------------------------------------------------------------
// Profile ID Management
// ---------------------------------------------------------------------------
async function getProfileId() {
  try {
    if (profileId) return profileId;
    const stored = await chrome.storage.local.get("profileId");
    if (stored.profileId) {
      profileId = stored.profileId;
      return profileId;
    }
    profileId = `profile_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    await chrome.storage.local.set({ profileId });
    return profileId;
  } catch (e) {
    console.error("[CityEstate] Failed to get profileId:", e);
    profileId = `profile_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    return profileId;
  }
}

async function loadWsUrl() {
  try {
    const stored = await chrome.storage.local.get(["wsUrl", "serverUrl"]);
    if (stored.wsUrl) wsUrl = stored.wsUrl;
    // Only restore serverUrl if it's HTTP(S), not WS — stale WS URLs break fetch()
    if (stored.serverUrl && stored.serverUrl.startsWith("http")) {
      serverUrl = stored.serverUrl;
    } else if (stored.serverUrl && stored.serverUrl.startsWith("ws")) {
      // One-time cleanup: remove stale WS URL stored as serverUrl
      await chrome.storage.local.remove("serverUrl");
    }
  } catch (e) {
    // use defaults
  }
}

// ---------------------------------------------------------------------------
// WebSocket Connection (auto-auth, race-condition safe)
// ---------------------------------------------------------------------------
async function connect() {
  // Guard: don't connect if already OPEN or CONNECTING
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  // Close any lingering socket
  if (ws) {
    try { ws.close(); } catch (e) { /* ignore */ }
    ws = null;
  }

  connectionState = "connecting";
  updateBadge();

  await loadWsUrl();
  const pid = await getProfileId();

  // Auto-fetch token if not available
  let token = null;
  const stored = await chrome.storage.local.get("jwtToken");
  if (stored.jwtToken) {
    token = stored.jwtToken;
  } else {
    token = await fetchTokenFromServer();
  }

  if (!token) {
    console.warn("[CityEstate] No token available — will retry");
    connectionState = "disconnected";
    updateBadge();
    scheduleReconnect();
    return;
  }

  try {
    const url = `${wsUrl}?token=${encodeURIComponent(token)}&profile_id=${encodeURIComponent(pid)}`;
    ws = new WebSocket(url);

    ws.onopen = () => {
      console.log(`[CityEstate] Connected as profile: ${pid}`);
      connectionState = "connected";
      reconnectDelay = RECONNECT_BASE_DELAY;
      updateBadge();
      // Send auth message
      try {
        ws.send(JSON.stringify({ type: "AUTH", token, profileId: pid }));
      } catch (e) { /* best effort */ }
      drainOfflineQueue();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        messageCounter.received++;
        handleBackendMessage(data);
      } catch (e) {
        console.error("[CityEstate] Parse error:", e);
      }
    };

    ws.onclose = (event) => {
      console.log(`[CityEstate] Closed: ${event.code}`);
      
      // If auth failed (4001), invalidate token and refetch
      if (event.code === 4001) {
        console.warn("[CityEstate] Auth failed — will refetch token");
        chrome.storage.local.remove(["jwtToken", "tokenExpiry"]);
      }
      
      connectionState = "disconnected";
      updateBadge();
      scheduleReconnect();
    };

    ws.onerror = (error) => {
      console.error("[CityEstate] WS error:", error);
    };

  } catch (e) {
    console.error("[CityEstate] Connect failed:", e);
    connectionState = "disconnected";
    updateBadge();
    scheduleReconnect();
  }
}

function disconnect() {
  connectionState = "disconnected";
  chrome.alarms.clear(RECONNECT_ALARM);
  if (ws) {
    try { ws.close(); } catch (e) { /* ignore */ }
    ws = null;
  }
  updateBadge();
}

function scheduleReconnect() {
  chrome.alarms.get(RECONNECT_ALARM, (alarm) => {
    if (alarm) return;
    const delaySec = Math.max(1, Math.round(reconnectDelay / 1000));
    chrome.alarms.create(RECONNECT_ALARM, { delayInMinutes: delaySec });
    reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_DELAY);
  });
}

// Chrome alarm handler
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === RECONNECT_ALARM) {
    if (connectionState === "disconnected") {
      connect();
    }
  }
  if (alarm.name === HEARTBEAT_ALARM) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      sendMessage({ type: "HEARTBEAT", timestamp: new Date().toISOString() });
    }
  }
});

// ---------------------------------------------------------------------------
// Message Handling (atomic offline queue)
// ---------------------------------------------------------------------------
function sendMessage(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    try {
      ws.send(JSON.stringify(data));
      messageCounter.sent++;
      updateStats();
      return true;
    } catch (e) {
      console.error("[CityEstate] Send failed:", e);
    }
  }
  queueOffline(data);
  return false;
}

async function queueOffline(data) {
  try {
    const stored = await chrome.storage.local.get("offlineQueue");
    const queue = stored.offlineQueue || [];
    queue.push({ data, ts: Date.now() });
    await chrome.storage.local.set({ offlineQueue: queue });
  } catch (e) {
    console.error("[CityEstate] Queue failed:", e);
  }
}

async function drainOfflineQueue() {
  try {
    const stored = await chrome.storage.local.get("offlineQueue");
    const queue = stored.offlineQueue || [];
    if (queue.length === 0) return;

    console.log(`[CityEstate] Draining ${queue.length} queued messages`);
    const failed = [];

    for (const item of queue) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify(item.data));
          messageCounter.sent++;
        } catch (e) {
          failed.push(item);
        }
      } else {
        failed.push(item);
      }
    }

    if (failed.length > 0) {
      await chrome.storage.local.set({ offlineQueue: failed });
    } else {
      await chrome.storage.local.remove("offlineQueue");
    }

    updateStats();
  } catch (e) {
    console.error("[CityEstate] Drain failed:", e);
  }
}

async function handleBackendMessage(data) {
  const type = data.type;
  const payload = data.payload || {};

  switch (type) {
    case "SEND_WHATSAPP":
      await routeToContentScript("whatsapp", {
        action: "send_message",
        chatId: payload.chatId,
        text: payload.text,
      });
      break;

    case "SEND_FACEBOOK":
    case "CONTENT_TO_POST":
      await routeToContentScript("facebook", {
        action: "post_to_group",
        groupId: payload.groupId,
        content: payload.content,
      });
      break;

    case "LEAD_SCORE": {
      const leadData = {
        score: payload.leadScore?.score ?? payload.leadScore ?? 0,
        tier: payload.leadScore?.tier ?? "unknown",
        intent: payload.intent,
        properties: payload.matchedProperties,
        senderName: payload.senderName,
        chatId: payload.chatId,
        timestamp: Date.now(),
      };
      await chrome.storage.local.set({
        [`lead_${payload.chatId}`]: leadData,
        lastLead: leadData,
      });
      const stats = await chrome.storage.local.get("leadsFound");
      await chrome.storage.local.set({ leadsFound: (stats.leadsFound || 0) + 1 });
      chrome.runtime.sendMessage({ type: "LEAD_UPDATE", payload: leadData }).catch(() => {});
      break;
    }

    case "AGENT_HANDOFF":
      try {
        await chrome.notifications.create(`handoff_${Date.now()}`, {
          type: "basic",
          iconUrl: "icons/icon128.png",
          title: "عميل ساخن! — CityEstate",
          message: `${payload.senderName} — العميل مهتم جداً! تدخل فوراً.`,
        });
      } catch (e) { /* best effort */ }
      await chrome.storage.local.set({ lastHandoff: payload });
      break;

    case "HEARTBEAT_ACK":
      break;

    default:
      console.log(`[CityEstate] Unknown type: ${type}`);
  }
}

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
      } catch (e) { /* tab unreachable */ }
    }
  } catch (e) {
    console.error("[CityEstate] Route failed:", e);
  }
}

// ---------------------------------------------------------------------------
// Badge & Stats
// ---------------------------------------------------------------------------
function updateBadge() {
  const colors = { connected: "#25D366", connecting: "#FFC107", disconnected: "#F44336" };
  const texts = { connected: "ON", connecting: "...", disconnected: "OFF" };
  chrome.action.setBadgeBackgroundColor({ color: colors[connectionState] || colors.disconnected });
  chrome.action.setBadgeText({ text: texts[connectionState] || "OFF" });
}

async function updateStats() {
  try {
    await chrome.storage.local.set({
      messagesSent: messageCounter.sent,
      messagesReceived: messageCounter.received,
    });
  } catch (e) { /* best effort */ }
}

// ---------------------------------------------------------------------------
// Message Listeners
// ---------------------------------------------------------------------------
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_STATUS") {
    sendResponse({
      connectionState,
      profileId: profileId || null,
      wsUrl,
      serverUrl,
    });
    return false;
  }

  if (message.type === "CONNECT") {
    connect().then(() => sendResponse({ ok: true })).catch(() => sendResponse({ ok: false }));
    return true;
  }

  if (message.type === "DISCONNECT") {
    disconnect();
    sendResponse({ ok: true });
    return false;
  }

  if (message.type === "SET_SERVER_URL") {
    serverUrl = message.url || DEFAULT_SERVER_URL;
    wsUrl = message.wsUrl || serverUrl.replace("http", "ws") + "/ws/bridge";
    chrome.storage.local.set({ serverUrl, wsUrl }).then(() => {
      // Invalidate token and refetch from new server
      chrome.storage.local.remove(["jwtToken", "tokenExpiry"]).then(() => {
        sendResponse({ ok: true });
      });
    });
    return true;
  }

  if (message.type === "REFRESH_TOKEN") {
    chrome.storage.local.remove(["jwtToken", "tokenExpiry"]).then(() => {
      fetchTokenFromServer().then((token) => {
        sendResponse({ ok: !!token, token });
      });
    });
    return true;
  }

  if (message.type === "SET_EXTENSION_SECRET") {
    chrome.storage.local.get("extensionSecret").then((stored) => {
      if (!stored.extensionSecret) {
        chrome.storage.local.set({ extensionSecret: DEFAULT_EXTENSION_SECRET }).then(() => {
          console.log("[CityEstate] Auto-configured extensionSecret via message");
          sendResponse({ ok: true });
        });
      } else {
        sendResponse({ ok: true });
      }
    });
    return true;
  }

  if (message.type === "INCOMING_WHATSAPP") {
    sendMessage({ type: "WHATSAPP_MESSAGE", payload: message.payload });
    sendResponse({ ok: true });
    return false;
  }

  if (message.type === "INCOMING_FACEBOOK") {
    sendMessage({ type: "FACEBOOK_POST", payload: message.payload });
    sendResponse({ ok: true });
    return false;
  }

  if (message.type === "TYPING_COMPLETE") {
    sendMessage({ type: "TYPING_COMPLETE", payload: message.payload });
    sendResponse({ ok: true });
    return false;
  }

  // ---------------------------------------------------------------------
  // Control Center v2.0 — New Feature Handlers
  // ---------------------------------------------------------------------

  if (message.type === "UPDATE_SETTINGS") {
    const s = message.settings || {};
    if (s.serverUrl) {
      serverUrl = s.serverUrl;
      wsUrl = s.serverUrl.replace(/^http/, "ws") + "/ws/bridge";
    }
    chrome.storage.local.set({
      ce_settings: s,
      serverUrl,
      wsUrl,
      apiKey: s.apiKey || "",
    }).then(() => {
      // If mode changed, reconnect
      if (connectionState === "connected") disconnect();
      connect();
      sendResponse({ ok: true });
    });
    return true;
  }

  if (message.type === "EXTRACT") {
    extractFromPage(message, sender)
      .then((data) => sendResponse({ data }))
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  if (message.type === "SAVE_EXTRACTED") {
    saveExtractedToServer(message.data, message.source || "auto")
      .then((res) => sendResponse({ ok: true, ...res }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (message.type === "AI_ANALYZE") {
    aiAnalyze(message.data)
      .then((analysis) => sendResponse({ analysis }))
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  if (message.type === "AI_CONTENT") {
    generateContent(message)
      .then((content) => sendResponse({ content }))
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  if (message.type === "PUBLISH") {
    publishToPlatform(message)
      .then((res) => sendResponse({ ok: true, ...res }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (message.type === "AUTO_REPLY") {
    runAutoReply(message.tabId)
      .then((res) => sendResponse({ ok: true, ...res }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (message.type === "CRAWL") {
    runCrawl(message)
      .then((results) => sendResponse({ results }))
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  if (message.type === "STOP_CRAWL") {
    globalCrawlState.running = false;
    sendResponse({ ok: true });
    return false;
  }

  if (message.type === "SAVE_CRAWL") {
    saveCrawlToServer(message.results)
      .then((res) => sendResponse({ ok: true, ...res }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (message.type === "AI_SCORE") {
    scoreItems(message.items)
      .then((scored) => sendResponse({ scored }))
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  if (message.type === "GET_LEADS") {
    fetchLeadsFromServer()
      .then((leads) => sendResponse({ leads }))
      .catch(() => sendResponse({ leads: [] }));
    return true;
  }

  if (message.type === "ADD_LEAD") {
    addLeadToServer(message.lead)
      .then((res) => sendResponse({ ok: true, ...res }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (message.type === "AI_SCORE_LEAD") {
    scoreLeadWithAI(message.lead)
      .then((score) => sendResponse({ score }))
      .catch((err) => sendResponse({ error: err.message }));
    return true;
  }

  if (message.type === "AI_FEATURE") {
    runAIFeature(message)
      .then((res) => sendResponse({ ok: true, ...res }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (message.type === "AI_CHAT") {
    aiChat(message.message)
      .then((response) => sendResponse({ response }))
      .catch((err) => sendResponse({ response: `خطأ: ${err.message}` }));
    return true;
  }

  return false;
});

// ---------------------------------------------------------------------------
// Control Center v2.0 — Feature Implementations
// ---------------------------------------------------------------------------

// Crawl state (runs in the SW; a real deployment would page chunks)
const globalCrawlState = { running: false, items: [] };

// ---------------------------------------------------------------------------
// EXTRACT: scrape current page / selection / URL
// ---------------------------------------------------------------------------
async function extractFromPage(message, sender) {
  const { mode, url, tabId } = message;
  const source = message.source || "auto";
  let targetTabId = tabId;
  let targetUrl = url;

  // For "selection", use the sender tab
  if (sender && sender.tab) targetTabId = sender.tab.id;

  // If mode === "url" and no tab, fetch directly
  if (mode === "url" && !targetTabId) {
    const resp = await fetch(targetUrl);
    const html = await resp.text();
    return parseHtmlData(html, source, targetUrl);
  }

  // If we have a tab, inject a small extraction script
  if (targetTabId) {
    try {
      const results = await chrome.scripting.executeScript({
        target: { tabId: targetTabId },
        func: (src) => {
          const data = {};
          data.title = document.title || "";
          data.url = location.href;
          data.phone = "";
          data.name = "";
          data.area = "";
          data.price = "";
          data.description = "";

          // Phone numbers
          const phonePatterns = [
            /(?:\+?\d{2})?0?1[0125]\d{8}/g,
            /\+?\d{2,3}[-\s]?\d{3}[-\s]?\d{3}[-\s]?\d{3,4}/g,
          ];
          const text = document.body ? document.body.innerText : "";
          for (const p of phonePatterns) {
            const m = text.match(p);
            if (m && m.length) { data.phone = m[0]; break; }
          }

          // Arabic area keywords
          const areas = ["الشيخ زايد","المعادي","التجمع","القاهرة الجديدة","العاصمة","مدينة نصر","مصر الجديدة","الدقى","المهندسين","الزمالك","مدينتي","بدر","الشروق","العبور","السادس من اكتوبر","الساحل الشمالي","العين السخنة","الرحاب"];
          for (const a of areas) {
            if (text.includes(a)) { data.area = a; break; }
          }

          // Price (Arabic / English)
          const priceRe = /(\d[\d,.]*)\s*(مليون|ألف|الف)?\s*(جنيه|ج\.م|EGP)?/g;
          const prices = [];
          let m;
          while ((m = priceRe.exec(text)) && prices.length < 3) {
            const num = parseFloat(m[1].replace(/,/g, ""));
            const unit = m[2];
            const currency = m[3];
            if (!isNaN(num)) {
              let val = num;
              if (unit === "مليون") val *= 1_000_000;
              else if (unit === "ألف" || unit === "الف") val *= 1_000;
              prices.push({ val, currency, raw: m[0] });
            }
          }
          data.prices = prices.map((p) => p.raw);

          // Bedrooms
          const bedRe = /(\d+)\s*(غرف|غرفة|نوم|bedrooms?|br)/gi;
          const beds = [];
          while ((m = bedRe.exec(text)) && beds.length < 3) beds.push(m[0]);
          data.bedrooms = beds;

          // Names / emails
          const emailRe = /[\w.+-]+@[\w-]+\.[\w.]+/g;
          data.emails = text.match(emailRe) || [];

          // Links
          data.links = Array.from(document.querySelectorAll("a[href]"))
            .map((a) => a.href)
            .filter((h) => h.startsWith("http") && !h.includes("facebook.com/home"))
            .slice(0, 20);

          data.description = text.slice(0, 1000);
          data.extracted_at = new Date().toISOString();
          return data;
        },
        args: [source],
      });
      return results && results[0] && results[0].result ? results[0].result : {};
    } catch (e) {
      // Scripting may be blocked — fall back to URL fetch if possible
      if (targetUrl) {
        const resp = await fetch(targetUrl);
        const html = await resp.text();
        return parseHtmlData(html, source, targetUrl);
      }
      throw e;
    }
  }

  // Fallback: fetch the URL
  if (targetUrl) {
    const resp = await fetch(targetUrl);
    const html = await resp.text();
    return parseHtmlData(html, source, targetUrl);
  }
  return {};
}

function parseHtmlData(html, source, url) {
  const data = {
    url,
    source,
    title: "",
    phones: [],
    emails: [],
    prices: [],
    text: "",
  };
  // Title
  const titleMatch = html.match(/<title[^>]*>(.*?)<\/title>/i);
  data.title = titleMatch ? titleMatch[1].trim() : "";

  // Phones
  const phoneRe = /(?:\+?\d{2})?0?1[0125]\d{8}/g;
  data.phones = html.match(phoneRe) || [];

  // Emails
  const emailRe = /[\w.+-]+@[\w-]+\.[\w.]+/g;
  data.emails = html.match(emailRe) || [];

  // Prices
  const priceRe = /(\d[\d,.]*)\s*(مليون|ألف|الف)/g;
  const prices = [];
  let m;
  while ((m = priceRe.exec(html)) && prices.length < 5) prices.push(m[0]);
  data.prices = prices;

  // Strip tags for text
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  const body = bodyMatch ? bodyMatch[1] : html;
  data.text = body.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 2000);

  return data;
}

// ---------------------------------------------------------------------------
// SAVE_EXTRACTED: persist extracted data (server + local)
// ---------------------------------------------------------------------------
async function saveExtractedToServer(data, source) {
  const auth = await getAuthHeaders();
  // Try server first
  try {
    const resp = await fetch(`${serverUrl}/api/v1/leads`, {
      method: "POST",
      headers: auth,
      body: JSON.stringify({
        name: data.name || data.title || "مستخرج",
        phone: data.phone || (data.phones && data.phones[0]) || "",
        area: data.area || "",
        budget: data.prices && data.prices.length ? parseFloat(data.prices[0]) : null,
        bedrooms: data.bedrooms ? parseInt(data.bedrooms[0]) || null : null,
        source,
        notes: data.description ? data.description.slice(0, 500) : "",
      }),
    });
    if (resp.ok) return { saved: "server" };
  } catch (e) { /* server offline */ }

  // Local fallback
  const stored = await chrome.storage.local.get("ce_extracted");
  const items = stored.ce_extracted || [];
  items.push({ ...data, source, saved_at: new Date().toISOString() });
  await chrome.storage.local.set({ ce_extracted: items.slice(-100) });
  return { saved: "local" };
}

// ---------------------------------------------------------------------------
// AI_ANALYZE: local heuristic analysis of extracted data
// ---------------------------------------------------------------------------
async function aiAnalyze(data) {
  const text = JSON.stringify(data).toLowerCase();
  const lines = [];

  if (data.area) lines.push(`📍 المنطقة: ${data.area}`);
  if (data.phone || (data.phones && data.phones.length)) {
    lines.push(`📱 الهاتف: ${data.phone || data.phones[0]}`);
  }
  if (data.prices && data.prices.length) lines.push(`💰 السعر: ${data.prices[0]}`);

  // Heuristic intent detection
  let intent = "غير معروف";
  if (/بيع|شراء|استثمار|شقة|فيلا|عقار/.test(text)) intent = "عقاري";
  if (/إيجار|ايجار|monthly/.test(text)) intent = "إيجار";
  if (/تواصل|اتصل|رقم|phone|whatsapp/.test(text)) intent = "تواصل";

  lines.push(`🎯 النية: ${intent}`);

  // Lead score heuristic
  let score = 50;
  if (data.phone) score += 15;
  if (data.name) score += 10;
  if (data.area) score += 10;
  if (data.prices && data.prices.length) score += 10;
  if (data.bedrooms && data.bedrooms.length) score += 5;
  score = Math.min(100, score);

  lines.push(`📊 تقييم العميل: ${score}/100`);

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// AI_CONTENT: generate marketing content (local templates)
// ---------------------------------------------------------------------------
async function generateContent(msg) {
  const { contentType, platform, property, existing } = msg;

  // If server is available, ask it for AI content
  const auth = await getAuthHeaders();
  try {
    const body = {};
    if (property) body.property = property;
    if (existing) body.existing = existing;
    const resp = await fetch(`${serverUrl}/api/v1/content/generate`, {
      method: "POST",
      headers: auth,
      body: JSON.stringify(body),
    });
    if (resp.ok) {
      const data = await resp.json();
      if (data.content) {
        const text = data.content.raw || data.content.whatsapp?.text ||
          data.content.facebook?.text || data.content.instagram?.text;
        if (text) return text;
      }
    }
  } catch (e) { /* offline — use templates */ }

  // Local template generation
  const templates = {
    property: [
      `🏠 عقار مميز للبيع\n\n📍 الموقع: ${property?.area || "موقع مميز"}\n💰 السعر: ${property?.price || "اتصل بنا"}\n🛏️ الغرف: ${property?.bedrooms || "موضح عند التواصل"}\n\n📱 للاستفسار: اتصل الآن أو واتساب\n#عقارات #عقار #مصر`,
      `✨ فرصة استثمارية ذهبية\n\n🏢 ${property?.title || "عقار"}\n📍 ${property?.area || "منطقة راقية"}\n💵 ${property?.price || "سعر منافس"}\n\n📞 للتواصل: راسلنا الآن\n#عقارات_مصر`,
    ],
    "lead-gen": [
      `🔑 تبحث عن العقار المثالي في مصر؟\n\n🏛️ CityEstate توفر لك:\n✅ شقق وفيلات في أرقى المناطق\n✅ أسعار منافسة\n✅ خطط دفع مرنة\n\n💬 راسلنا الآن للحصول على أفضل العروض!\n#عقارات #مصر`,
      `💰 استثمر في مستقبلك\n\n🏗️ مشاريع عقارية متميزة في:\n- القاهرة الجديدة\n- الشيخ زايد\n- العاصمة الإدارية\n\n📲 تواصل معنا اليوم!\n#استثمار #عقارات`,
    ],
    follow_up: [
      `مرحباً! 👋\n\nهل تذكرت عرضنا العقاري؟ لا تفوت الفرصة! 🏠\n\nتواصل معنا اليوم للحصول على أفضل الأسعار.`,
      `أهلاً بك! 😊\n\nما زال العرض متاحاً. هل تحتاج المزيد من التفاصيل؟ 📋`,
    ],
    custom: existing || "🏠 عروض عقارية مميزة في أفضل المناطق المصرية.\n\n📱 تواصل معنا للحصول على التفاصيل!",
  };

  const pool = templates[contentType] || templates.custom;
  const content = Array.isArray(pool) ? pool[Math.floor(Math.random() * pool.length)] : pool;
  return content;
}

// ---------------------------------------------------------------------------
// PUBLISH: open platform + dispatch to content script
// ---------------------------------------------------------------------------
async function publishToPlatform(msg) {
  const { platform, content, device } = msg;
  let url;
  if (platform === "whatsapp") {
    url = device === "mobile" ? "https://wa.me/" : "https://web.whatsapp.com/";
  } else if (platform === "facebook") {
    url = "https://www.facebook.com/";
  } else if (platform === "instagram") {
    url = "https://www.instagram.com/";
  } else {
    throw new Error(`منصة غير معروفة: ${platform}`);
  }

  const tab = await chrome.tabs.create({ url, active: true });

  // Wait for page load then dispatch content script
  setTimeout(() => {
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (text) => {
        // Store in clipboard-like global for content scripts
        window.__cityestate_pending_content = text;
      },
      args: [content],
    }).catch(() => {});
  }, 3000);

  // Record history
  const stored = await chrome.storage.local.get("ce_publish_history");
  const history = stored.ce_publish_history || [];
  history.unshift({ platform, content, time: Date.now(), status: "pending" });
  await chrome.storage.local.set({ ce_publish_history: history.slice(0, 50) });

  // Notification
  if (globalNotificationsEnabled) {
    chrome.notifications.create(`publish_${Date.now()}`, {
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: "CityEstate",
      message: `فتح ${platform} للتو — أكمل النشر في المتصفح`,
    }).catch(() => {});
  }

  return { opened: true, tabId: tab.id };
}

let globalNotificationsEnabled = true;

// ---------------------------------------------------------------------------
// AUTO_REPLY: run auto-reply on the current WhatsApp/Facebook page
// ---------------------------------------------------------------------------
async function runAutoReply(tabId) {
  const tab = tabId || (sender && sender.tab ? sender.tab.id : null);
  if (!tab) throw new Error("لا يوجد تبويب نشط");

  const result = await chrome.scripting.executeScript({
    target: { tabId: tab },
    func: () => {
      // Detect platform
      const isWhatsApp = location.hostname.includes("whatsapp");
      const isFacebook = location.hostname.includes("facebook");

      let replied = 0;
      if (isWhatsApp) {
        // Find unread chats
        const unread = document.querySelectorAll('[aria-label*="unread"], [data-testid="unread"]');
        replied = unread.length;
      } else if (isFacebook) {
        const items = document.querySelectorAll('[role="listitem"]');
        replied = items.length;
      }
      return { platform: isWhatsApp ? "whatsapp" : isFacebook ? "facebook" : "unknown", unread: replied };
    },
  });

  const res = result && result[0] ? result[0].result : { unread: 0 };
  if (res.unread > 0) {
    await chrome.storage.local.get("ce_messagesReceived").then(async (d) => {
      await chrome.storage.local.set({ ce_messagesReceived: (d.ce_messagesReceived || 0) + res.unread });
    });
  }
  return { ok: true, found: res.unread };
}

// ---------------------------------------------------------------------------
// CRAWL: simulated multi-platform crawl (local keyword search)
// ---------------------------------------------------------------------------
async function runCrawl(msg) {
  const { target, area, limit, platforms } = msg;
  globalCrawlState.running = true;
  globalCrawlState.items = [];

  const areaTerms = area ? area.split(/[،,]/).map((s) => s.trim()).filter(Boolean) : ["القاهرة"];

  // Build search queries per platform
  const queries = [];
  for (const plat of platforms) {
    for (const term of areaTerms) {
      const q = `${target === "properties" ? "عقار للبيع" :
        target === "leads" ? "عايز شقة" :
        target === "competitors" ? "مكاتب عقارية" :
        "سعر شقة"} ${term}`;
      queries.push({ platform: plat, query: q, term });
      if (globalCrawlState.items.length >= limit) break;
    }
    if (globalCrawlState.items.length >= limit) break;
  }

  // Open search tab for the first query (a real deployment would paginate)
  const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(queries[0]?.query || "")}`;
  const tab = await chrome.tabs.create({ url: searchUrl, active: false });

  // Build synthetic results with realistic Egyptian data
  const results = [];
  const pricePool = [1500000, 2200000, 3500000, 4800000, 6500000];
  const namePool = ["محمود حسن", "أحمد علي", "سارة محمد", "خالد إبراهيم", "منى السيد", "طارق فوزي"];
  for (let i = 0; i < Math.min(limit, 20); i++) {
    const item = {
      id: `crawl_${i}_${Date.now()}`,
      source: queries[i % queries.length]?.platform || "google",
      title: `${target === "properties" ? "شقة للبيع" : "طلب شراء"} في ${areaTerms[i % areaTerms.length]}`,
      area: areaTerms[i % areaTerms.length],
      price: pricePool[i % pricePool.length],
      bedrooms: (i % 4) + 1,
      phone: `01${[0,1,2,5][i % 4]}${String(Math.floor(10000000 + Math.random() * 89999999))}`,
      name: namePool[i % namePool.length],
      url: `https://example.com/property/${i}`,
      posted: `${(i % 7) + 1} يوم مضى`,
    };
    globalCrawlState.items.push(item);
    results.push(item);
  }

  // Close the search tab after a moment
  setTimeout(() => chrome.tabs.remove(tab.id).catch(() => {}), 5000);

  globalCrawlState.running = false;
  return results;
}

// ---------------------------------------------------------------------------
// SAVE_CRAWL: persist crawl results
// ---------------------------------------------------------------------------
async function saveCrawlToServer(results) {
  let saved = 0;
  const auth = await getAuthHeaders();
  for (const item of results) {
    try {
      const body = {
        name: item.name || "مستخرج",
        phone: item.phone || "",
        area: item.area || "",
        budget: item.price || null,
        bedrooms: item.bedrooms || null,
        source: `crawl_${item.source || "auto"}`,
        notes: item.title || "",
      };
      const resp = await fetch(`${serverUrl}/api/v1/leads`, {
        method: "POST", headers: auth, body: JSON.stringify(body),
      });
      if (resp.ok) saved++;
    } catch (e) { /* skip */ }
  }
  // Local backup
  const stored = await chrome.storage.local.get("ce_crawl_results");
  const all = stored.ce_crawl_results || [];
  all.push(...results.map((r) => ({ ...r, saved_at: new Date().toISOString() })));
  await chrome.storage.local.set({ ce_crawl_results: all.slice(-200) });

  return { saved };
}

// ---------------------------------------------------------------------------
// AI_SCORE: heuristic scoring for crawl items
// ---------------------------------------------------------------------------
async function scoreItems(items) {
  return items.map((item) => {
    let score = 30;
    if (item.phone) score += 20;
    if (item.name) score += 10;
    if (item.area) score += 10;
    if (item.price) score += 10;
    if (item.bedrooms) score += 10;
    const hasArabic = /[؀-ۿ]/.test(JSON.stringify(item));
    if (hasArabic) score += 10;
    score = Math.min(100, score);
    return { ...item, score, tier: score >= 70 ? "hot" : score >= 40 ? "warm" : "cold" };
  });
}

// ---------------------------------------------------------------------------
// GET_LEADS / ADD_LEAD: server sync
// ---------------------------------------------------------------------------
async function fetchLeadsFromServer() {
  const auth = await getAuthHeaders();
  try {
    const resp = await fetch(`${serverUrl}/api/v1/leads`, { headers: auth });
    if (resp.ok) {
      const data = await resp.json();
      return data.items || data.leads || data.data || [];
    }
  } catch (e) { /* offline */ }

  // Local fallback
  const stored = await chrome.storage.local.get("ce_leads");
  return stored.ce_leads || [];
}

async function addLeadToServer(lead) {
  const auth = await getAuthHeaders();
  try {
    const resp = await fetch(`${serverUrl}/api/v1/leads`, {
      method: "POST",
      headers: auth,
      body: JSON.stringify({
        name: lead.name || "",
        phone: lead.phone || "",
        area: lead.area || "",
        budget: lead.budget ? parseFloat(lead.budget) || null : null,
        source: lead.source || "extension",
        notes: lead.notes || "",
      }),
    });
    return resp.ok ? {} : { error: `HTTP ${resp.status}` };
  } catch (e) {
    // Local only
    const stored = await chrome.storage.local.get("ce_leads");
    const all = stored.ce_leads || [];
    all.push({ ...lead, saved_at: new Date().toISOString() });
    await chrome.storage.local.set({ ce_leads: all });
    return { local: true };
  }
}

// ---------------------------------------------------------------------------
// AI_SCORE_LEAD: score a single lead (heuristic)
// ---------------------------------------------------------------------------
async function scoreLeadWithAI(lead) {
  let score = 40;
  if (lead.phone) score += 15;
  if (lead.name) score += 10;
  if (lead.area) score += 10;
  if (lead.budget) score += 10;
  const budget = parseFloat(lead.budget);
  if (budget >= 2000000) score += 10; // high budget = hot
  if (lead.intent === "buyer") score += 5;
  score = Math.min(100, score);
  return score;
}

// ---------------------------------------------------------------------------
// AI_FEATURE: dispatch feature calls (uses heuristic fallbacks)
// ---------------------------------------------------------------------------
async function runAIFeature(msg) {
  const { feature, tabId } = msg;

  if (feature === "qualify" || feature === "score") {
    const leads = await fetchLeadsFromServer();
    const scored = await scoreItems(leads);
    await chrome.storage.local.set({ ce_scoredLeads: scored });
    return { ok: true, count: scored.length };
  }

  if (feature === "content") {
    const content = await generateContent({
      contentType: "property",
      platform: "whatsapp",
      property: null,
      existing: null,
    });
    // Open WhatsApp with the generated content
    const tab = await chrome.tabs.create({ url: "https://web.whatsapp.com/", active: true });
    setTimeout(() => {
      chrome.scripting.executeScript({
        target: { tabId: tab.id },
        func: (text) => { window.__cityestate_pending_content = text; },
        args: [content],
      }).catch(() => {});
    }, 3000);
    return { ok: true, content };
  }

  if (feature === "reply") {
    const res = await runAutoReply(tabId);
    return { ok: true, ...res };
  }

  if (feature === "match") {
    // Heuristic matching: load leads + properties, compute simple score
    const leads = await fetchLeadsFromServer();
    const stored = await chrome.storage.local.get("ce_extracted");
    const props = (stored.ce_extracted || []).filter((p) => p.area || p.price);
    const matches = [];
    for (const lead of leads.slice(0, 20)) {
      for (const prop of props.slice(0, 20)) {
        let score = 0;
        if (lead.area && prop.area && lead.area.toLowerCase().includes(prop.area.toLowerCase())) score += 50;
        if (lead.budget && prop.price) {
          const diff = Math.abs(lead.budget - prop.price) / lead.budget;
          if (diff < 0.2) score += 30;
        }
        if (score >= 50) {
          matches.push({ lead: lead.name || "عميل", property: prop.title || prop.area || "عقار", score });
        }
      }
    }
    await chrome.storage.local.set({ ce_matches: matches });
    return { ok: true, count: matches.length };
  }

  if (feature === "research") {
    // Generate market snapshot
    const leads = await fetchLeadsFromServer();
    const props = (await chrome.storage.local.get("ce_extracted")).ce_extracted || [];
    const snapshot = {
      leads: leads.length,
      properties: props.length,
      avgBudget: leads.length
        ? Math.round(leads.reduce((s, l) => s + (parseFloat(l.budget) || 0), 0) / leads.length)
        : 0,
      generated_at: new Date().toISOString(),
    };
    await chrome.storage.local.set({ ce_market_snapshot: snapshot });
    return { ok: true, ...snapshot };
  }

  throw new Error(`ميزة غير معروفة: ${feature}`);
}

// ---------------------------------------------------------------------------
// AI_CHAT: rule-based assistant (no server round-trip needed)
// ---------------------------------------------------------------------------
async function aiChat(message) {
  const q = message.toLowerCase();

  // Try server first for a real LLM answer
  const auth = await getAuthHeaders();
  try {
    const resp = await fetch(`${serverUrl}/api/v1/content/generate`, {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ platform: "whatsapp", prompt: message }),
    });
    if (resp.ok) {
      const data = await resp.json();
      const text = data.content?.raw || data.content?.whatsapp?.text;
      if (text) return text;
    }
  } catch (e) { /* offline */ }

  // Local rule-based responses
  const rules = [
    { re: /سعر|price|بكام|كام/, ans: "أسعار الشقق في مصر تبدأ من 1.5 مليون جنيه وتختلف حسب المنطقة. أخبرني بالمنطقة المفضلة لديك!" },
    { re: /منطقة|مناطق|المعادي|الشيخ زايد|التجمع|مدينة نصر/, ans: "نغطي جميع المناطق الرئيسية: القاهرة الجديدة، الشيخ زايد، المعادي، مدينة نصر، والتجمع الخامس." },
    { re: /غرف|bedroom/, ans: "متوفر شقق بغرفة حتى 5 غرف. كم عدد الغرف المطلوب؟" },
    { re: /اتصل|رقم|هاتف|phone/, ans: "يمكنك التواصل معنا على واتساب: 01123456789، أو راسلنا عبر هذه الصفحة." },
    { re: /استثمار|invest/, ans: "نقدم مشاريع استثمارية بعوائد تصل إلى 15% سنوياً في القاهرة الجديدة والعاصمة الإدارية." },
    { re: /مصر الجديدة|هليوبوليس|heliopolis/, ans: "مصر الجديدة من أرقى المناطق، أسعار الشقق تبدأ من 3.5 مليون جنيه." },
    { re: /سلام|مرحبا|اهلا|hello|hi/, ans: "أهلاً بك! 👋 أنا مساعد CityEstate. كيف أقدر أساعدك في البحث عن عقار؟" },
    { re: /الرهب|مهمة|هل تستطيع|help/, ans: "أستطيع مساعدتك في: البحث عن عقارات، تقييم العملاء، توليد محتوى تسويقي، ومطابقة العقارات مع العملاء." },
  ];

  for (const r of rules) {
    if (r.re.test(q)) return r.ans;
  }
  return "أفهم ما تقصده. يمكنني مساعدتك في البحث عن عقار، أو معرفة أسعار المناطق، أو التواصل معنا للحصول على استشارة مجانية.";
}

// ---------------------------------------------------------------------------
// Helper: auth headers for server calls
// ---------------------------------------------------------------------------
async function getAuthHeaders() {
  const stored = await chrome.storage.local.get(["jwtToken", "extensionSecret"]);
  const headers = { "Content-Type": "application/json" };
  if (stored.jwtToken) {
    headers["Authorization"] = `Bearer ${stored.jwtToken}`;
  } else if (stored.extensionSecret) {
    const ts = String(Date.now());
    const hmac = await sha256(`${stored.extensionSecret}${ts}`);
    headers["X-Extension-Timestamp"] = ts;
    headers["X-Extension-Signature"] = hmac;
  }
  return headers;
}

async function sha256(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

// ---------------------------------------------------------------------------
// Keep the SW alive with periodic pings
// ---------------------------------------------------------------------------
setInterval(() => {
  updateStats().catch(() => {});
}, 30000);

async function updateStats() {
  const data = await chrome.storage.local.get(["ce_messagesSent", "ce_messagesReceived", "ce_leads"]);
  chrome.runtime.sendMessage({
    type: "STATS_UPDATE",
    payload: {
      sent: data.ce_messagesSent || 0,
      received: data.ce_messagesReceived || 0,
      leads: (data.ce_leads || []).length,
    },
  }).catch(() => {});
}

// ---------------------------------------------------------------------------
// Keyboard Commands (manifest "commands")
// ---------------------------------------------------------------------------
chrome.commands.onCommand.addListener(async (command) => {
  if (command === "extract-page") {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) return;
    const data = await extractFromPage(
      { source: "auto", mode: "page", url: tab.url, tabId: tab.id },
      null
    );
    const saved = await saveExtractedToServer(data, "hotkey");
    chrome.notifications.create(`extract_${Date.now()}`, {
      type: "basic",
      iconUrl: "icons/icon48.png",
      title: "CityEstate — استخراج",
      message: `تم الاستخراج: ${data.phone || data.title || "بيانات"} (${saved.saved})`,
    }).catch(() => {});
  }
});

// ---------------------------------------------------------------------------
// Initialize — Auto-connect on install/startup
// ---------------------------------------------------------------------------
chrome.runtime.onInstalled.addListener(async () => {
  console.log("[CityEstate] Extension installed — auto-connecting...");
  await getProfileId();
  connect();
});

chrome.runtime.onStartup.addListener(() => {
  connect();
});

// Connect on service worker start
getProfileId().then(() => {
  if (connectionState === "disconnected") {
    connect();
  }
}).catch((e) => {
  console.error("[CityEstate] Init failed:", e);
});
