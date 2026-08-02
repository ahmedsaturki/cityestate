/**
 * CityEstate Standalone — Popup Script
 * ======================================
 * Controls the popup UI. Reads data from chrome.storage.
 * NO backend calls — everything is local.
 */

document.addEventListener("DOMContentLoaded", () => {
  // ---------------------------------------------------------------------------
  // DOM refs
  // ---------------------------------------------------------------------------
  const totalLeadsEl = document.getElementById("totalLeads");
  const platinumLeadsEl = document.getElementById("platinumLeads");
  const goldLeadsEl = document.getElementById("goldLeads");
  const silverLeadsEl = document.getElementById("silverLeads");
  const leadsList = document.getElementById("leadsList");
  const notesList = document.getElementById("notesList");
  const noteInput = document.getElementById("noteInput");
  const addNoteBtn = document.getElementById("addNoteBtn");
  const templatesList = document.getElementById("templatesList");
  const areasList = document.getElementById("areasList");
  const openWhatsApp = document.getElementById("openWhatsApp");
  const openFacebook = document.getElementById("openFacebook");
  const autoReplyToggle = document.getElementById("autoReplyToggle");
  const notifToggle = document.getElementById("notifToggle");

  // ---------------------------------------------------------------------------
  // Tab switching
  // ---------------------------------------------------------------------------
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
    });
  });

  // ---------------------------------------------------------------------------
  // Load stats
  // ---------------------------------------------------------------------------
  async function loadStats() {
    try {
      const data = await chrome.storage.local.get(["stats", "leads", "settings"]);
      const stats = data.stats || {};
      const leads = data.leads || [];
      const settings = data.settings || {};

      totalLeadsEl.textContent = leads.length;
      platinumLeadsEl.textContent = stats.leadsByTier?.platinum || 0;
      goldLeadsEl.textContent = stats.leadsByTier?.gold || 0;
      silverLeadsEl.textContent = stats.leadsByTier?.silver || 0;

      // Settings
      autoReplyToggle.checked = settings.autoReplyEnabled !== false;
      notifToggle.checked = settings.showNotifications !== false;

      // Render leads
      renderLeads(leads);
    } catch (e) {
      console.warn("loadStats failed:", e);
    }
  }

  // ---------------------------------------------------------------------------
  // Render leads
  // ---------------------------------------------------------------------------
  function renderLeads(leads) {
    if (!leads || leads.length === 0) {
      leadsList.innerHTML = '<div class="empty-state">لا يوجد عملاء بعد</div>';
      return;
    }

    leadsList.innerHTML = leads.slice(0, 50).map((lead) => {
      const score = lead.score || 0;
      const tier = lead.tier || "rejected";
      const timeAgo = lead._ts ? getTimeAgo(lead._ts) : "";
      const detail = [
        lead.area,
        lead.propertyType,
        lead.budget ? `${(lead.budget / 1000).toFixed(0)}K` : null,
      ].filter(Boolean).join(" • ") || lead.text?.substring(0, 40) || "---";

      return `
        <div class="lead-item" data-chatid="${lead.chatId || ""}">
          <div class="lead-score-badge ${tier}">${score}</div>
          <div class="lead-info">
            <div class="lead-name">${escapeHtml(lead.senderName || "عميل")}</div>
            <div class="lead-detail">${escapeHtml(detail)}</div>
          </div>
          <div class="lead-time">${timeAgo}</div>
        </div>
      `;
    }).join("");
  }

  // ---------------------------------------------------------------------------
  // Notes
  // ---------------------------------------------------------------------------
  async function loadNotes() {
    try {
      const data = await chrome.storage.local.get("notes");
      const notes = data.notes || [];
      renderNotes(notes);
    } catch (e) {}
  }

  function renderNotes(notes) {
    if (!notes || notes.length === 0) {
      notesList.innerHTML = '<div class="empty-state">لا توجد ملاحظات</div>';
      return;
    }

    notesList.innerHTML = notes.map((note) => `
      <div class="note-item">
        <span class="note-text">${escapeHtml(note.text || "")}</span>
        <button class="note-delete" data-id="${note._id}">✕</button>
      </div>
    `).join("");

    // Delete handlers
    notesList.querySelectorAll(".note-delete").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        const data = await chrome.storage.local.get("notes");
        const notes = (data.notes || []).filter((n) => n._id !== id);
        await chrome.storage.local.set({ notes });
        loadNotes();
      });
    });
  }

  addNoteBtn.addEventListener("click", async () => {
    const text = noteInput.value.trim();
    if (!text) return;

    const data = await chrome.storage.local.get("notes");
    const notes = data.notes || [];
    notes.unshift({
      text,
      _ts: Date.now(),
      _id: `note_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
    });
    if (notes.length > 200) notes.length = 200;
    await chrome.storage.local.set({ notes });
    noteInput.value = "";
    loadNotes();
  });

  noteInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") addNoteBtn.click();
  });

  // ---------------------------------------------------------------------------
  // Templates (from CityEstateAutoReply)
  // ---------------------------------------------------------------------------
  function loadTemplates() {
    // Templates are defined inline since we can't access the content script's window object
    const templates = [
      { key: "welcome", label: "ترحيب — عميل جديد", preview: "مرحباً... أهلاً بيك في مجموعة عقارات premium..." },
      { key: "budget_high", label: "ميزانية عالية (>1.5M)", preview: "ممتاز! ميزانيتك تفتحلك أفضل الخيارات..." },
      { key: "budget_medium", label: "ميزانية متوسطة", preview: "عندنا خيارات كتير في السادات..." },
      { key: "area_sadat", label: "استفسار — مدينة السادات", preview: "مدينة السادات من أحسن المناطق للاستثمار!" },
      { key: "urgent", label: "عميل عاجل", preview: "فاهم إن الموضوع عاجل!" },
      { key: "villa", label: "استفسار — فيلا", preview: "فيلات السادات من أحسن الخيارات!" },
      { key: "commercial", label: "استفسار — وحدة تجارية", preview: "الوحدات التجارية فرصة ذهبية!" },
      { key: "industrial", label: "استفسار — صناعي", preview: "المنطقة الصناعية من أقوى المناطق!" },
      { key: "follow_up", label: "متابعة", preview: "عايز أتأكد إنك لقيت اللي بتدور عليه" },
      { key: "closing", label: "إغلاق", preview: "لو عايز نكمل، أنا جاهز!" },
    ];

    templatesList.innerHTML = templates.map((t) => `
      <div class="template-item" data-key="${t.key}">
        <div class="template-label">${t.label}</div>
        <div class="template-preview">${t.preview}</div>
      </div>
    `).join("");
  }

  // ---------------------------------------------------------------------------
  // Areas (from CityEstateKnowledge)
  // ---------------------------------------------------------------------------
  function loadAreas() {
    const areas = [
      {
        name: "المنطقة 7 — الشريط المميز",
        desc: "منطقة مميزة على الرئيسي، تجارية وسكنية",
        price: "1.5M - 5M جنيه",
        highlights: "شارع رئيسي • قريبة من الخدمات • موقع تجاري ممتاز",
      },
      {
        name: "المنطقة 9",
        desc: "منطقة سكنية هادئة مع خدمات متنوعة",
        price: "800K - 3M جنيه",
        highlights: "هادئة • قريبة من المدارس • بنية تحتية جيدة",
      },
      {
        name: "المنطقة 15",
        desc: "منطقة نامية بفرص استثمارية",
        price: "600K - 2M جنيه",
        highlights: "أسعار مناسبة • نمو سريع • قريبة من المنطقة الصناعية",
      },
      {
        name: "المنطقة الصناعية",
        desc: "قلب الصناعة في السادات — تصدير 7 مليار دولار",
        price: "1M - 10M جنيه",
        highlights: "تصدير 7 مليار دولار • ميناء • طرق سريعة",
      },
      {
        name: "المنطقة الحرة — Free Zone",
        desc: "منطقة حرة للتصدير والاستيراد",
        price: "2M - 15M جنيه",
        highlights: "إعفاء ضريبي • تصدير مباشر • قرب من الميناء",
      },
    ];

    areasList.innerHTML = areas.map((a) => `
      <div class="area-item">
        <div class="area-name">${a.name}</div>
        <div class="area-desc">${a.desc}</div>
        <div class="area-price">الأسعار: ${a.price}</div>
        <div class="area-highlights">${a.highlights}</div>
      </div>
    `).join("");
  }

  // ---------------------------------------------------------------------------
  // Settings
  // ---------------------------------------------------------------------------
  autoReplyToggle.addEventListener("change", () => {
    chrome.storage.local.get("settings").then((data) => {
      const settings = data.settings || {};
      settings.autoReplyEnabled = autoReplyToggle.checked;
      chrome.storage.local.set({ settings });
    });
  });

  notifToggle.addEventListener("change", () => {
    chrome.storage.local.get("settings").then((data) => {
      const settings = data.settings || {};
      settings.showNotifications = notifToggle.checked;
      chrome.storage.local.set({ settings });
    });
  });

  // ---------------------------------------------------------------------------
  // Quick actions
  // ---------------------------------------------------------------------------
  openWhatsApp.addEventListener("click", () => {
    chrome.tabs.create({ url: "https://web.whatsapp.com" });
  });

  openFacebook.addEventListener("click", () => {
    chrome.tabs.create({ url: "https://www.facebook.com/groups/" });
  });

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------
  function getTimeAgo(ts) {
    const diff = Date.now() - ts;
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "الآن";
    if (mins < 60) return `${mins}د`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}س`;
    const days = Math.floor(hrs / 24);
    return `${days}ي`;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // ---------------------------------------------------------------------------
  // Listen for real-time updates
  // ---------------------------------------------------------------------------
  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === "LEAD_UPDATE") {
      loadStats();
    }
  });

  // ---------------------------------------------------------------------------
  // Initialize
  // ---------------------------------------------------------------------------
  loadStats();
  loadNotes();
  loadTemplates();
  loadAreas();
});
