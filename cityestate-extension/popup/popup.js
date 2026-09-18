/**
 * CityEstate Control Center — Popup Script v2.0
 * ===============================================
 * Comprehensive control panel for browser automation.
 * Handles: extraction, publishing, crawling, leads, AI, settings.
 */

// ---------------------------------------------------------------------------
// Utility helpers
// ---------------------------------------------------------------------------
function $(id) { return document.getElementById(id); }

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("show"));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}

function fmtTime(ts) {
  if (!ts) return "";
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

async function sendToBackground(msg) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(msg, (response) => {
      if (chrome.runtime.lastError) {
        resolve({ error: chrome.runtime.lastError.message });
      } else {
        resolve(response);
      }
    });
  });
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let settings = {
  serverUrl: "http://localhost:8000",
  apiKey: "",
  operationMode: "bridge",
  speedLevel: "normal",
  autoReplyEnabled: true,
  notificationsEnabled: true,
};

let currentLeads = [];
let extractedData = null;
let crawlResults = [];
let crawlRunning = false;

// ---------------------------------------------------------------------------
// Tab Navigation
// ---------------------------------------------------------------------------
function initTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      $(`tab-${tab}`).classList.add("active");

      // Load data on demand
      if (tab === "leads") loadLeads();
      if (tab === "dashboard") loadDashboard();
      if (tab === "publish") loadPublishHistory();
    });
  });
}

// ---------------------------------------------------------------------------
// Connection Status
// ---------------------------------------------------------------------------
async function updateConnectionStatus() {
  const el = $("connection-status");
  const text = $("status-text");
  try {
    const result = await sendToBackground({ type: "GET_STATUS" });
    if (result && result.connected) {
      el.className = "status connected";
      text.textContent = "متصل";
    } else if (result && result.connecting) {
      el.className = "status connecting";
      text.textContent = "جاري الاتصال...";
    } else {
      el.className = "status disconnected";
      text.textContent = "غير متصل";
    }
  } catch (e) {
    el.className = "status disconnected";
    text.textContent = "خطأ";
  }
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
async function loadDashboard() {
  const data = await chrome.storage.local.get([
    "ce_leads", "ce_messagesSent", "ce_messagesReceived", "ce_scoredLeads",
  ]);
  $("stat-leads").textContent = (data.ce_leads || []).length;
  $("stat-sent").textContent = data.ce_messagesSent || 0;
  $("stat-received").textContent = data.ce_messagesReceived || 0;
  $("stat-scored").textContent = (data.ce_scoredLeads || []).length;

  const activity = await chrome.storage.local.get("ce_activity");
  const list = $("activity-list");
  const activities = activity.ce_activity || [];
  if (activities.length === 0) {
    list.innerHTML = '<div class="empty-state">لا يوجد نشاط بعد</div>';
  } else {
    list.innerHTML = activities.slice(0, 10).map((a) => `
      <div class="activity-item">
        <span class="activity-icon">${a.icon || "📌"}</span>
        <span class="activity-text">${a.text}</span>
        <span class="activity-time">${fmtTime(a.time)}</span>
      </div>
    `).join("");
  }
}

async function addActivity(text, icon = "📌") {
  const data = await chrome.storage.local.get("ce_activity");
  const activities = data.ce_activity || [];
  activities.unshift({ text, icon, time: Date.now() });
  await chrome.storage.local.set({ ce_activity: activities.slice(0, 50) });
}

// ---------------------------------------------------------------------------
// Data Extraction
// ---------------------------------------------------------------------------
function initExtraction() {
  document.querySelectorAll('input[name="extract-mode"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      const mode = document.querySelector('input[name="extract-mode"]:checked').value;
      $("url-input-group").classList.toggle("hidden", mode !== "url");
    });
  });

  $("btn-extract").addEventListener("click", extractFromPage);
  $("btn-scan-page").addEventListener("click", extractFromPage);
  $("btn-scan-all").addEventListener("click", extractAllPages);
  $("btn-copy-extract").addEventListener("click", copyExtractedData);
  $("btn-save-extract").addEventListener("click", saveExtractedData);
  $("btn-ai-analyze").addEventListener("click", aiAnalyzeData);
}

async function extractFromPage() {
  const source = $("extract-source").value;
  const mode = document.querySelector('input[name="extract-mode"]:checked').value;
  let url = null;

  if (mode === "url") {
    url = $("custom-url").value.trim();
    if (!url) {
      showToast("أدخل الرابط أولاً", "error");
      return;
    }
  }

  $("footer-status").textContent = "جاري الاستخراج...";
  try {
    const tab = await getActiveTab();
    const result = await sendToBackground({
      type: "EXTRACT",
      source,
      mode,
      url: url || tab.url,
      tabId: tab.id,
    });

    if (result && result.data) {
      extractedData = result.data;
      $("extract-results").classList.remove("hidden");
      $("extracted-data").textContent = formatData(result.data);
      showToast(`تم استخراج ${Object.keys(result.data).length} حقل`, "success");
      await addActivity("استخراج بيانات من صفحة", "🔍");
    } else if (result && result.error) {
      showToast(result.error, "error");
    } else {
      showToast("لم يتم العثور على بيانات", "error");
    }
  } catch (e) {
    showToast(`خطأ: ${e.message}`, "error");
  }
  $("footer-status").textContent = "جاهز";
}

async function extractAllPages() {
  showToast("جاري استخراج كل الصفحات المفتوحة...", "info");
  const tabs = await chrome.tabs.query({});
  let count = 0;
  for (const tab of tabs) {
    if (!tab.url || !tab.url.startsWith("http")) continue;
    const result = await sendToBackground({
      type: "EXTRACT",
      source: "auto",
      mode: "page",
      url: tab.url,
      tabId: tab.id,
    });
    if (result && result.data) count++;
  }
  showToast(`تم استخراج بيانات من ${count} صفحة`, "success");
}

function formatData(data) {
  if (typeof data === "string") return data;
  if (Array.isArray(data)) {
    return data.map((item, i) => `--- عنصر ${i + 1} ---\n${JSON.stringify(item, null, 2)}`).join("\n\n");
  }
  return JSON.stringify(data, null, 2);
}

function copyExtractedData() {
  if (!extractedData) return;
  const text = typeof extractedData === "string" ? extractedData : JSON.stringify(extractedData, null, 2);
  navigator.clipboard.writeText(text).then(() => {
    showToast("تم النسخ إلى الحافظة", "success");
  });
}

async function saveExtractedData() {
  if (!extractedData) return;
  try {
    const result = await sendToBackground({
      type: "SAVE_EXTRACTED",
      data: extractedData,
      source: $("extract-source").value,
    });
    if (result && result.ok) {
      showToast("تم حفظ البيانات", "success");
      await addActivity("حفظ بيانات مستخرجة", "💾");
    } else {
      showToast(result && result.error ? result.error : "فشل الحفظ", "error");
    }
  } catch (e) {
    showToast(`خطأ: ${e.message}`, "error");
  }
}

async function aiAnalyzeData() {
  if (!extractedData) return;
  showToast("جاري تحليل البيانات بالـ AI...", "info");
  try {
    const result = await sendToBackground({
      type: "AI_ANALYZE",
      data: extractedData,
    });
    if (result && result.analysis) {
      $("extracted-data").textContent = result.analysis;
      showToast("تم التحليل", "success");
    } else {
      showToast("فشل التحليل", "error");
    }
  } catch (e) {
    showToast(`خطأ: ${e.message}`, "error");
  }
}

// ---------------------------------------------------------------------------
// Publishing
// ---------------------------------------------------------------------------
let selectedPlatform = "whatsapp";

function initPublishing() {
  document.querySelectorAll(".platform-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".platform-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      selectedPlatform = btn.dataset.platform;
    });
  });

  $("btn-generate-content").addEventListener("click", generateContent);
  $("btn-publish").addEventListener("click", publishContent);
  $("btn-schedule").addEventListener("click", scheduleContent);
  $("btn-auto-reply").addEventListener("click", triggerAutoReply);
}

async function generateContent() {
  const type = $("content-type").value;
  const existing = $("publish-content").value.trim();

  // Try to find a property on the current page
  let propertyData = null;
  try {
    const tab = await getActiveTab();
    const result = await sendToBackground({
      type: "EXTRACT",
      source: "property-listing",
      mode: "page",
      url: tab.url,
      tabId: tab.id,
    });
    if (result && result.data) propertyData = result.data;
  } catch (e) { /* ignore */ }

  showToast("جاري توليد المحتوى بالـ AI...", "info");
  try {
    const result = await sendToBackground({
      type: "AI_CONTENT",
      contentType: type,
      platform: selectedPlatform,
      property: propertyData,
      existing: existing,
    });
    if (result && result.content) {
      $("publish-content").value = result.content;
      showToast("تم توليد المحتوى!", "success");
      await addActivity("توليد محتوى بالـ AI", "🤖");
    } else {
      showToast("فشل توليد المحتوى", "error");
    }
  } catch (e) {
    showToast(`خطأ: ${e.message}`, "error");
  }
}

async function publishContent() {
  const content = $("publish-content").value.trim();
  if (!content) {
    showToast("اكتب المحتوى أولاً", "error");
    return;
  }

  showToast(`جاري النشر على ${selectedPlatform}...`, "info");
  try {
    const result = await sendToBackground({
      type: "PUBLISH",
      platform: selectedPlatform,
      content,
      device: $("target-device").value,
    });

    if (result && result.ok) {
      showToast(`تم النشر على ${selectedPlatform}!`, "success");
      $("publish-content").value = "";
      await addActivity(`نشر على ${selectedPlatform}`, "📤");
      loadPublishHistory();
    } else {
      showToast(result && result.error ? result.error : "فشل النشر", "error");
    }
  } catch (e) {
    showToast(`خطأ: ${e.message}`, "error");
  }
}

function scheduleContent() {
  const content = $("publish-content").value.trim();
  if (!content) {
    showToast("اكتب المحتوى أولاً", "error");
    return;
  }
  // Ask for schedule time
  const when = prompt("بعد كم دقيقة تنشر؟ (5-1440)");
  if (!when || isNaN(when)) return;
  const minutes = Math.max(5, Math.min(1440, parseInt(when)));

  chrome.alarms.create("ce_scheduled_publish", { delayInMinutes: minutes });

  showToast(`سيتم النشر بعد ${minutes} دقيقة`, "success");
  chrome.storage.local.set({
    ce_scheduled_publish: { content, platform: selectedPlatform, at: Date.now() + minutes * 60000 },
  });
  addActivity(`جدولة نشر على ${selectedPlatform} بعد ${minutes}د`, "⏰");
}

async function triggerAutoReply() {
  showToast("جاري تنفيذ الرد التلقائي...", "info");
  try {
    const tab = await getActiveTab();
    const result = await sendToBackground({
      type: "AUTO_REPLY",
      tabId: tab.id,
    });
    if (result && result.ok) {
      showToast("تم تنفيذ الرد التلقائي", "success");
      await addActivity("تنفيذ رد تلقائي", "💬");
    } else {
      showToast(result && result.error ? result.error : "لا يوجد محادثات جديدة", "info");
    }
  } catch (e) {
    showToast(`خطأ: ${e.message}`, "error");
  }
}

async function loadPublishHistory() {
  const data = await chrome.storage.local.get("ce_publish_history");
  const history = data.ce_publish_history || [];
  const log = $("publish-log");
  if (history.length === 0) {
    log.innerHTML = '<div class="empty-state">لا يوجد نشر بعد</div>';
  } else {
    log.innerHTML = history.slice(0, 20).map((h) => `
      <div class="activity-item">
        <span class="activity-icon">📤</span>
        <span class="activity-text">${h.platform}: ${h.content.slice(0, 40)}...</span>
        <span class="activity-time">${fmtTime(h.time)}</span>
      </div>
    `).join("");
  }
}

// ---------------------------------------------------------------------------
// Crawling
// ---------------------------------------------------------------------------
function initCrawling() {
  $("btn-start-crawl").addEventListener("click", startCrawl);
  $("btn-stop-crawl").addEventListener("click", stopCrawl);
  $("btn-save-crawl").addEventListener("click", saveCrawlResults);
  $("btn-ai-score").addEventListener("click", aiScoreCrawlResults);
}

async function startCrawl() {
  const target = $("crawl-target").value;
  const area = $("crawl-area").value.trim();
  const limit = parseInt($("crawl-limit").value) || 50;

  if (!area) {
    showToast("أدخل المنطقة أولاً", "error");
    return;
  }

  crawlRunning = true;
  $("btn-start-crawl").disabled = true;
  $("btn-stop-crawl").disabled = false;
  $("crawl-progress").classList.remove("hidden");
  $("crawl-progress-bar").style.width = "10%";
  $("crawl-status").textContent = "جاري البحث...";

  const platforms = [];
  document.querySelectorAll('input[name="crawl-platform"]:checked').forEach((p) => {
    platforms.push(p.value);
  });

  try {
    const result = await sendToBackground({
      type: "CRAWL",
      target,
      area,
      limit,
      platforms,
    });

    $("crawl-progress-bar").style.width = "100%";
    $("crawl-status").textContent = "اكتمل الزحف";

    if (result && result.results) {
      crawlResults = result.results;
      $("crawl-results").classList.remove("hidden");
      $("crawl-data").textContent = formatData(crawlResults);
      showToast(`تم العثور على ${crawlResults.length} نتيجة`, "success");
      await addActivity(`زحف: ${target} في ${area}`, "🕷️");
    } else {
      $("crawl-status").textContent = "لم يتم العثور على نتائج";
      showToast(result && result.error ? result.error : "لا نتائج", "info");
    }
  } catch (e) {
    $("crawl-status").textContent = "خطأ في الزحف";
    showToast(`خطأ: ${e.message}`, "error");
  } finally {
    crawlRunning = false;
    $("btn-start-crawl").disabled = false;
    $("btn-stop-crawl").disabled = true;
  }
}

function stopCrawl() {
  crawlRunning = false;
  $("btn-start-crawl").disabled = false;
  $("btn-stop-crawl").disabled = true;
  $("crawl-status").textContent = "تم الإيقاف";
  sendToBackground({ type: "STOP_CRAWL" });
}

async function saveCrawlResults() {
  if (crawlResults.length === 0) return;
  try {
    const result = await sendToBackground({
      type: "SAVE_CRAWL",
      results: crawlResults,
    });
    if (result && result.ok) {
      showToast(`تم حفظ ${crawlResults.length} نتيجة`, "success");
      await addActivity(`حفظ ${crawlResults.length} نتيجة زحف`, "💾");
    } else {
      showToast(result && result.error ? result.error : "فشل الحفظ", "error");
    }
  } catch (e) {
    showToast(`خطأ: ${e.message}`, "error");
  }
}

async function aiScoreCrawlResults() {
  if (crawlResults.length === 0) return;
  showToast("جاري تقييم النتائج بالـ AI...", "info");
  try {
    const result = await sendToBackground({
      type: "AI_SCORE",
      items: crawlResults,
    });
    if (result && result.scored) {
      crawlResults = result.scored;
      $("crawl-data").textContent = formatData(crawlResults);
      showToast("تم التقييم", "success");
    } else {
      showToast("فشل التقييم", "error");
    }
  } catch (e) {
    showToast(`خطأ: ${e.message}`, "error");
  }
}

// ---------------------------------------------------------------------------
// Leads
// ---------------------------------------------------------------------------
function initLeads() {
  $("btn-add-lead").addEventListener("click", addLead);
  $("lead-search").addEventListener("input", filterLeads);
  $("lead-filter").addEventListener("change", filterLeads);
  $("btn-lead-whatsapp").addEventListener("click", () => contactLead("whatsapp"));
  $("btn-lead-call").addEventListener("click", () => contactLead("call"));
  $("btn-lead-score").addEventListener("click", scoreSelectedLead);
}

async function loadLeads() {
  const data = await chrome.storage.local.get("ce_leads");
  currentLeads = data.ce_leads || [];

  // Also try to fetch from server if connected
  const serverData = await sendToBackground({ type: "GET_LEADS" });
  if (serverData && serverData.leads && serverData.leads.length > 0) {
    currentLeads = serverData.leads;
  }

  renderLeads();
}

function renderLeads() {
  const search = $("lead-search").value.toLowerCase();
  const filter = $("lead-filter").value;
  const list = $("leads-list");

  const filtered = currentLeads.filter((lead) => {
    const name = (lead.name || lead.client_name || "").toLowerCase();
    const phone = lead.phone || "";
    const score = lead.score || 0;
    const matchesSearch = !search || name.includes(search) || phone.includes(search);
    const matchesFilter = filter === "all" ||
      (filter === "hot" && score >= 70) ||
      (filter === "warm" && score >= 40 && score < 70) ||
      (filter === "cold" && score < 40);
    return matchesSearch && matchesFilter;
  });

  if (filtered.length === 0) {
    list.innerHTML = '<div class="empty-state">لا يوجد عملاء مطابقين</div>';
    return;
  }

  list.innerHTML = filtered.map((lead, i) => {
    const score = lead.score || 0;
    const band = score >= 70 ? "hot" : score >= 40 ? "warm" : "cold";
    const bandLabel = score >= 70 ? "🔥 ساخن" : score >= 40 ? "🟡 دافئ" : "❄️ بارد";
    return `
      <div class="lead-card ${band}" data-idx="${i}">
        <div class="lead-card-header">
          <span class="lead-card-name">${escapeHtml(lead.name || lead.client_name || `عميل ${i + 1}`)}</span>
          <span class="lead-card-badge ${band}">${bandLabel}</span>
        </div>
        <div class="lead-card-meta">
          <span>📱 ${escapeHtml(lead.phone || "-")}</span>
          ${lead.area ? `<span>📍 ${escapeHtml(lead.area)}</span>` : ""}
          ${lead.budget ? `<span>💰 ${escapeHtml(String(lead.budget))}</span>` : ""}
        </div>
      </div>
    `;
  }).join("");

  list.querySelectorAll(".lead-card").forEach((card) => {
    card.addEventListener("click", () => showLeadDetail(currentLeads[card.dataset.idx]));
  });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = String(str ?? "");
  return div.innerHTML;
}

function filterLeads() {
  renderLeads();
}

function showLeadDetail(lead) {
  $("lead-detail").classList.remove("hidden");
  $("lead-name").textContent = lead.name || lead.client_name || "عميل";
  const score = lead.score || 0;
  $("lead-info").innerHTML = `
    <div>📱 الهاتف: <strong>${escapeHtml(lead.phone || "-")}</strong></div>
    ${lead.area ? `<div>📍 المنطقة: <strong>${escapeHtml(lead.area)}</strong></div>` : ""}
    ${lead.budget ? `<div>💰 الميزانية: <strong>${escapeHtml(String(lead.budget))}</strong></div>` : ""}
    ${lead.bedrooms ? `<div>🛏️ الغرف: <strong>${lead.bedrooms}</strong></div>` : ""}
    <div>🎯 التقييم: <strong>${score}/100 (${score >= 70 ? "ساخن" : score >= 40 ? "دافئ" : "بارد"})</strong></div>
    ${lead.intent ? `<div>💡 النية: <strong>${escapeHtml(lead.intent)}</strong></div>` : ""}
    ${lead.source ? `<div>🔗 المصدر: <strong>${escapeHtml(lead.source)}</strong></div>` : ""}
  `;
}

async function addLead() {
  const name = prompt("اسم العميل:");
  if (!name) return;
  const phone = prompt("رقم الهاتف:");
  if (!phone) return;
  const area = prompt("المنطقة (اختياري):") || "";
  const budget = prompt("الميزانية (اختياري):") || "";

  const lead = { name, phone, area, budget, score: 50, intent: "buyer", source: "manual", created_at: new Date().toISOString() };
  currentLeads.push(lead);
  await chrome.storage.local.set({ ce_leads: currentLeads });

  // Also try to save to server
  await sendToBackground({ type: "ADD_LEAD", lead });
  renderLeads();
  showToast("تم إضافة العميل", "success");
}

async function contactLead(method) {
  const lead = currentLeads.find((l) => l.name === $("lead-name").textContent);
  if (!lead || !lead.phone) {
    showToast("رقم الهاتف غير متوفر", "error");
    return;
  }
  if (method === "whatsapp") {
    const url = `https://wa.me/${lead.phone.replace(/\D/g, "")}`;
    chrome.tabs.create({ url });
  } else if (method === "call") {
    const url = `tel:${lead.phone.replace(/\D/g, "")}`;
    chrome.tabs.create({ url: `https://wa.me/${lead.phone.replace(/\D/g, "")}` });
    showToast("تم فتح الواتساب", "success");
  }
}

async function scoreSelectedLead() {
  const lead = currentLeads.find((l) => l.name === $("lead-name").textContent);
  if (!lead) return;
  showToast("جاري تقييم العميل بالـ AI...", "info");
  try {
    const result = await sendToBackground({ type: "AI_SCORE_LEAD", lead });
    if (result && result.score !== undefined) {
      lead.score = result.score;
      await chrome.storage.local.set({ ce_leads: currentLeads });
      showLeadDetail(lead);
      renderLeads();
      showToast(`التقييم: ${result.score}/100`, "success");
      await addActivity(`تقييم عميل: ${lead.name} (${result.score})`, "🎯");
    } else {
      showToast("فشل التقييم", "error");
    }
  } catch (e) {
    showToast(`خطأ: ${e.message}`, "error");
  }
}

// ---------------------------------------------------------------------------
// AI Features
// ---------------------------------------------------------------------------
function initAI() {
  document.querySelectorAll(".ai-feature-card .action-btn").forEach((btn) => {
    btn.addEventListener("click", () => runAIFeature(btn.closest(".ai-feature-card").dataset.feature));
  });

  $("btn-ai-send").addEventListener("click", sendAIChat);
  $("ai-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendAIChat();
  });
}

async function runAIFeature(feature) {
  const labels = {
    qualify: "تصنيف العملاء",
    content: "توليد المحتوى",
    reply: "الرد الذكي",
    score: "تقييم العروض",
    match: "المطابقة الذكية",
    research: "بحث السوق",
  };
  showToast(`جاري تشغيل ${labels[feature]}...`, "info");
  try {
    const tab = await getActiveTab();
    const result = await sendToBackground({ type: "AI_FEATURE", feature, tabId: tab.id });
    if (result && result.ok) {
      showToast(`تم ${labels[feature]}`, "success");
      await addActivity(`تشغيل ${labels[feature]}`, "🤖");
    } else {
      showToast(result && result.error ? result.error : "فشل العملية", "error");
    }
  } catch (e) {
    showToast(`خطأ: ${e.message}`, "error");
  }
}

async function sendAIChat() {
  const input = $("ai-input");
  const message = input.value.trim();
  if (!message) return;

  const messages = $("ai-messages");
  messages.innerHTML += `
    <div class="ai-message user">
      <div class="message-avatar">👤</div>
      <div class="message-content">${escapeHtml(message)}</div>
    </div>
  `;
  input.value = "";
  messages.scrollTop = messages.scrollHeight;

  const typing = `
    <div class="ai-message bot">
      <div class="message-avatar">🤖</div>
      <div class="message-content">جاري التفكير...</div>
    </div>
  `;
  messages.innerHTML += typing;

  try {
    const result = await sendToBackground({ type: "AI_CHAT", message });
    messages.querySelector(".ai-message.bot:last-child .message-content").textContent =
      (result && result.response) || "عذراً، لا أستطيع الرد الآن.";
  } catch (e) {
    messages.querySelector(".ai-message.bot:last-child .message-content").textContent = "خطأ في الاتصال.";
  }
  messages.scrollTop = messages.scrollHeight;
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
async function loadSettings() {
  const data = await chrome.storage.local.get("ce_settings");
  if (data.ce_settings) settings = { ...settings, ...data.ce_settings };

  $("server-url").value = settings.serverUrl;
  $("api-key").value = settings.apiKey;
  $("operation-mode").value = settings.operationMode;
  $("speed-level").value = settings.speedLevel;
  $("auto-reply-enabled").checked = settings.autoReplyEnabled;
  $("notifications-enabled").checked = settings.notificationsEnabled;
}

function initSettings() {
  $("btn-save-settings").addEventListener("click", saveSettings);
  $("btn-reset-settings").addEventListener("click", resetSettings);
}

async function saveSettings() {
  settings = {
    serverUrl: $("server-url").value.trim(),
    apiKey: $("api-key").value.trim(),
    operationMode: $("operation-mode").value,
    speedLevel: $("speed-level").value,
    autoReplyEnabled: $("auto-reply-enabled").checked,
    notificationsEnabled: $("notifications-enabled").checked,
  };
  await chrome.storage.local.set({ ce_settings: settings });
  await sendToBackground({ type: "UPDATE_SETTINGS", settings });
  showToast("تم حفظ الإعدادات", "success");
}

async function resetSettings() {
  await chrome.storage.local.remove("ce_settings");
  await loadSettings();
  showToast("تمت إعادة التعيين", "success");
}

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------
async function exportData() {
  const data = await chrome.storage.local.get(null);
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  await chrome.downloads.download({ url, filename: "cityestate-export.json" });
  showToast("تم تصدير البيانات", "success");
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
  initTabs();
  initExtraction();
  initPublishing();
  initCrawling();
  initLeads();
  initAI();
  initSettings();
  loadSettings();

  $("btn-export").addEventListener("click", exportData);
  $("btn-add-lead").addEventListener("click", addLead);

  updateConnectionStatus();
  loadDashboard();
});
