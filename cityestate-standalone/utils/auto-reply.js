/**
 * CityEstate Standalone — Auto-Reply Templates
 * ==============================================
 * Pre-built response templates for common real estate inquiries.
 * All templates are for El Sadat City premium properties.
 * No API needed — text replacement with lead data.
 */

window.CityEstateAutoReply = (function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Template categories
  // ---------------------------------------------------------------------------
  const TEMPLATES = {
    // --- Premium property inquiry responses ---
    welcome: {
      label: "ترحيب — عميل جديد",
      text: "مرحباً {name} 👋\n\nأهلاً بيك في مجموعة عقارات premium في مدينة السادات.\n\nعندنا خيارات مميزة:\n- فيلات وكمبوندات بأفضل المواقع\n- وحدات تجارية وصناعية\n- استثمارات بأعلى عائد\n\nقولي محتاج إيه وأنا هساعدك تلاقي اللي يناسبك 😊",
    },

    budget_high: {
      label: "ميزانية عالية (>1.5M)",
      text: "{name}، ممتاز! ميزانيتك تفتحلك أفضل الخيارات في السادات.\n\nعندنا:\n- فيلات standalone من 2.5M\n- وحدات تجارية في المناطق المميزة\n- أراضي استثمارية بأفضل الأسعار\n\nعايز أبعتلك التفاصيل؟ أو تحب تزور المعرض؟",
    },

    budget_medium: {
      label: "ميزانية متوسطة (500K-1.5M)",
      text: "{name}، أوكي! عندنا خيارات كتير في السادات تناسب ميزانيتك.\n\nشوف:\n- شقق في كمبوندات مغلقة\n- دوبلكسات بتشطيبات عالية\n- استوديوهات استثمارية\n\nعايز أبعتلك صور وأسعار؟",
    },

    budget_low: {
      label: "ميزانية أقل من 500K",
      text: "{name}، عندنا كمان خيارات في السادات بأسعار مناسبة.\n\n- شقق في المناطق الصناعية\n- وحدات استوديو\n- أراضي للبناء\n\nعايز تعرف التفاصيل؟",
    },

    area_sadat: {
      label: "استفسار — مدينة السادات",
      text: "{name}، مدينة السادات من أحسن المناطق للاستثمار! 🏗️\n\n- 90km من القاهرة، 60km من الإسكندرية\n- منطقة صناعية بتصدير 7 مليار دولار\n- بنية تحتية متطورة\n\nعندنا وحدات في:\n- المنطقة 7 (الشريط المميزة)\n- المنطقة 9\n- المنطقة 15\n\nعايز تعرف أكتر؟",
    },

    urgent: {
      label: "عميل عاجل",
      text: "{name}، فاهم إن الموضوع عاجل! ⚡\n\nهبعتلك OPTIONS متاحة NOW:\n- فيلات جاهزة للسكن\n- وحدات تجارية فتحت حديثاً\n\nعايز أبعتلك التفاصيل في الواتساب؟ أو تيجي المعرض النهاردة؟",
    },

    villa: {
      label: "استفسار — فيلا",
      text: "{name}، فيلات السادات من أحسن الخيارات! 🏡\n\n- فيلات standalone من 250م²\n- مساحات خضرة خاصة\n-aman 24/7\n- قرب من الخدمات\n\nالأسعار تبدأ من 2.5M جنيه\n\nعايز أبعتلك صور وتفاصيل؟",
    },

    commercial: {
      label: "استفسار — وحدة تجارية",
      text: "{name}، الوحدات التجارية في السادات فرصة ذهبية! 🏪\n\n- مواقع على الشارع الرئيسي\n- قريبة من المنطقة الصناعية\n- عائد إيجاري ممتاز\n\nالأسعار تبدأ من 1.5M\n\nعايز تعرف التفاصيل؟",
    },

    industrial: {
      label: "استفسار — صناعي",
      text: "{name}، المنطقة الصناعية في السادات من أقوى المناطق في مصر! 🏭\n\n- تصدير 7 مليار دولار سنوياً\n- بنية تحتية متطورة\n- قرب من الميناء والطرق السريعة\n\nعندنا أراضي ومباني صناعية.\n\nعايز تعرف الأسعار؟",
    },

    follow_up: {
      label: "متابعة",
      text: "{name}، عايز أتأكد إنك لقيت اللي بتدور عليه 😊\n\nعندنا جديد في السادات:\n- وحدات جديدة دخلت السوق\n- عروض خاصة لفترة محدودة\n\nلو عندك أي سؤال، أنا موجود!",
    },

    closing: {
      label: "إغلاق",
      text: "{name}، لو عايز نكمل، أنا جاهز! 🤝\n\n- بعتلك الصور والتفاصيل\n- نحدد موعد زيارة\n- نتفق على الأسعار\n\nقولي ونبدأ!",
    },

    // --- Intent extraction helpers ---
    no_budget: {
      label: "طلب ميزانية",
      text: "{name}، عشان أقدر أساعدك أكتر، ممكن تقولي الميزانية اللي بتفكر فيها؟\n\nده هيساعدني أبعتلك أحسن الخيارات اللي تناسبك 😊",
    },

    no_area: {
      label: "طلب منطقة",
      text: "{name}، عايز منطقة معينة في السادات؟\n\n- المنطقة 7 (الشريط المميزة)\n- المنطقة 9\n- المنطقة 15\n- المنطقة الصناعية\n\nقولي اللي يناسبك!",
    },
  };

  // ---------------------------------------------------------------------------
  // Select best template based on lead score + intent
  // ---------------------------------------------------------------------------
  function selectTemplate(scoreResult, intent) {
    if (scoreResult.tier === "rejected") return null;

    const { propertyType, budget, area, timeline } = intent || {};

    // Urgent gets priority
    if (timeline === "urgent") return TEMPLATES.urgent;

    // High budget
    if (budget && budget >= 1500000) return TEMPLATES.budget_high;

    // Property type specific
    if (propertyType === "villa" || propertyType === "compound") return TEMPLATES.villa;
    if (propertyType === "commercial") return TEMPLATES.commercial;
    if (propertyType === "industrial") return TEMPLATES.industrial;

    // Medium budget
    if (budget && budget >= 500000) return TEMPLATES.budget_medium;

    // Area-specific
    if (area && /سادات|سادس|منطقة/.test(area)) return TEMPLATES.area_sadat;

    // Low budget
    if (budget && budget < 500000) return TEMPLATES.budget_low;

    // Default: welcome
    return TEMPLATES.welcome;
  }

  // ---------------------------------------------------------------------------
  // Fill template with lead data
  // ---------------------------------------------------------------------------
  function fillTemplate(template, data) {
    if (!template) return null;
    let text = template.text;
    text = text.replace(/\{name\}/g, data.senderName || "عميل");
    text = text.replace(/\{budget\}/g, data.budget ? `${(data.budget / 1000).toFixed(0)}K` : "---");
    text = text.replace(/\{area\}/g, data.area || "---");
    text = text.replace(/\{propertyType\}/g, data.propertyType || "---");
    return text;
  }

  // ---------------------------------------------------------------------------
  // Generate auto-reply
  // ---------------------------------------------------------------------------
  function generateReply(scoreResult, intent, senderName) {
    const template = selectTemplate(scoreResult, intent);
    if (!template) return null;
    return fillTemplate(template, {
      senderName,
      budget: intent?.budget,
      area: intent?.area,
      propertyType: intent?.propertyType,
    });
  }

  // ---------------------------------------------------------------------------
  // Get all template names (for UI)
  // ---------------------------------------------------------------------------
  function listTemplates() {
    return Object.entries(TEMPLATES).map(([key, val]) => ({
      key,
      label: val.label,
      preview: val.text.substring(0, 80) + "...",
    }));
  }

  // ---------------------------------------------------------------------------
  // Get template by key
  // ---------------------------------------------------------------------------
  function getTemplate(key) {
    return TEMPLATES[key] || null;
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    generateReply,
    selectTemplate,
    fillTemplate,
    listTemplates,
    getTemplate,
    TEMPLATES,
  };
})();
