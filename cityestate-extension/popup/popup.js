/**
 * CityEstate Bridge — Popup Script (Auto-Auth)
 * ================================================
 * Controls the extension popup UI.
 * Shows connection status, lead info, quick actions.
 * NO manual JWT input — auto-fetches token from server.
 */

document.addEventListener("DOMContentLoaded", () => {
  const statusCard = document.getElementById("statusCard");
  const statusIndicator = document.getElementById("statusIndicator");
  const statusLabel = document.getElementById("statusLabel");
  const statusDetail = document.getElementById("statusDetail");
  const profileIdEl = document.getElementById("profileId");
  const wsUrlEl = document.getElementById("wsUrl");
  const messagesSentEl = document.getElementById("messagesSent");
  const leadsFoundEl = document.getElementById("leadsFound");
  const lastLeadCard = document.getElementById("lastLeadCard");
  const leadBadge = document.getElementById("leadBadge");
  const leadScoreEl = document.getElementById("leadScore");
  const leadName = document.getElementById("leadName");
  const leadArea = document.getElementById("leadArea");
  const connectBtn = document.getElementById("connectBtn");
  const disconnectBtn = document.getElementById("disconnectBtn");
  const autoAuthStatus = document.getElementById("autoAuthStatus");
  const refreshTokenBtn = document.getElementById("refreshToken");
  const extensionSecretInput = document.getElementById("extensionSecret");
  const saveSecretBtn = document.getElementById("saveSecretBtn");

  const statusText = {
    connected: { label: "متصل", detail: "Connected to AI Brain" },
    connecting: { label: "جاري الاتصال...", detail: "Connecting..." },
    disconnected: { label: "غير متصل", detail: "Disconnected" },
  };

  const autoAuthText = {
    ok: "متصل تلقائياً",
    pending: "جاري التحقق...",
    failed: "فشل — انقر لتجديد",
    no_token: "لم يتم الإدخال",
  };

  // ---------------------------------------------------------------------------
  // Update UI
  // ---------------------------------------------------------------------------
  function updateStatus(state) {
    const info = statusText[state] || statusText.disconnected;
    statusIndicator.className = `status-indicator ${state}`;
    statusLabel.textContent = info.label;
    statusDetail.textContent = info.detail;
  }

  function updateAutoAuth(state) {
    autoAuthStatus.textContent = autoAuthText[state] || autoAuthText.pending;
  }

  function updateProfileInfo(data) {
    if (data.profileId) {
      profileIdEl.textContent = data.profileId.slice(0, 20) + "...";
    }
    if (data.wsUrl) {
      wsUrlEl.textContent = data.wsUrl.replace("ws://", "").replace("wss://", "");
    }
  }

  function showLastLead(lead) {
    if (!lead) {
      lastLeadCard.style.display = "none";
      return;
    }

    lastLeadCard.style.display = "block";

    let score = 0;
    if (lead.leadScore) {
      score = typeof lead.leadScore === "object" ? (lead.leadScore.score || 0) : lead.leadScore;
    } else if (lead.score !== undefined) {
      score = lead.score;
    }

    if (score >= 80) {
      leadBadge.textContent = "عميل ساخن";
      leadBadge.style.color = "#FF6B6B";
    } else if (score >= 50) {
      leadBadge.textContent = "عميل دافئ";
      leadBadge.style.color = "#FFC107";
    } else {
      leadBadge.textContent = "عميل بارد";
      leadBadge.style.color = "#888";
    }

    leadScoreEl.textContent = `${score}/100`;
    leadName.textContent = lead.senderName || "---";
    leadArea.textContent = (lead.intent && lead.intent.area) || "---";
  }

  // ---------------------------------------------------------------------------
  // Load State
  // ---------------------------------------------------------------------------
  async function loadState() {
    try {
      const response = await chrome.runtime.sendMessage({ type: "GET_STATUS" });
      updateStatus(response.connectionState);
      updateProfileInfo(response);
    } catch (e) {
      updateStatus("disconnected");
    }

    try {
      const stored = await chrome.storage.local.get([
        "messagesSent",
        "leadsFound",
        "lastLead",
        "jwtToken",
      ]);

      messagesSentEl.textContent = stored.messagesSent || 0;
      leadsFoundEl.textContent = stored.leadsFound || 0;

      if (stored.lastLead) {
        showLastLead(stored.lastLead);
      }

      // Auto-auth status
      if (stored.jwtToken) {
        updateAutoAuth("ok");
      } else {
        updateAutoAuth("no_token");
      }
    } catch (e) {
      console.warn("[CityEstate] Storage read failed:", e);
    }
  }

  // ---------------------------------------------------------------------------
  // Event Listeners
  // ---------------------------------------------------------------------------
  connectBtn.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "CONNECT" }, (response) => {
      if (response && response.ok) {
        updateStatus("connecting");
      }
    });
    updateStatus("connecting");
  });

  disconnectBtn.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "DISCONNECT" }, (response) => {
      updateStatus("disconnected");
    });
  });

  refreshTokenBtn.addEventListener("click", () => {
    updateAutoAuth("pending");
    chrome.runtime.sendMessage({ type: "REFRESH_TOKEN" }, (response) => {
      if (response && response.ok) {
        updateAutoAuth("ok");
      } else {
        updateAutoAuth("failed");
      }
    });
  });

  saveSecretBtn.addEventListener("click", async () => {
    const value = (extensionSecretInput.value || "").trim();
    if (value.length < 16) {
      alert("EXTENSION_SHARED_SECRET must be at least 16 characters.");
      return;
    }
    await chrome.storage.local.set({ extensionSecret: value });
    extensionSecretInput.value = "";
    updateAutoAuth("pending");
    chrome.runtime.sendMessage({ type: "REFRESH_TOKEN" }, (response) => {
      if (response && response.ok) {
        updateAutoAuth("ok");
      } else {
        updateAutoAuth("failed");
      }
    });
  });

  // Auto-setup: if extensionSecret not configured, trigger auto-configure
  const initSecret = async () => {
    const stored = await chrome.storage.local.get("extensionSecret");
    if (!stored.extensionSecret) {
      chrome.runtime.sendMessage({ type: "SET_EXTENSION_SECRET" }, (response) => {
        if (response && response.ok) {
          updateAutoAuth("ok");
        }
      });
    }
  };
  initSecret();

  // Listen for lead updates
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === "LEAD_UPDATE") {
      showLastLead(message.payload);
      chrome.storage.local.get("leadsFound").then((data) => {
        leadsFoundEl.textContent = data.leadsFound || 0;
      }).catch(() => {});
    }
  });

  // ---------------------------------------------------------------------------
  // Initialize
  // ---------------------------------------------------------------------------
  loadState();
});
