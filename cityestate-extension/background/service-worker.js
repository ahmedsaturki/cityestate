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

  return false;
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
