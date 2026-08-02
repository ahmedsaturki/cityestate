/**
 * CityEstate Standalone — Lead Scoring Engine
 * =============================================
 * Local rules-based lead scoring. No API needed.
 * Mirrors backend scoring logic for premium El Sadat City properties.
 *
 * Scoring weights:
 *   property_type: +20 (industrial/commercial), +15 (villa/compound), +8 (apartment)
 *   budget: +35 (>3M), +25 (1.5-3M), +15 (500K-1.5M), +8 (<500K)
 *   timeline: +10 (urgent/flexible), +5 (exploring)
 *   area_el_sadat: +10
 *   seriousness: +10
 *   origin_whatsapp: +10
 *   broker_penalty: -30
 *
 * Tiers: platinum (≥80), gold (60-79), silver (40-59), rejected (<40)
 */

window.CityEstateLeadScorer = (function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Constants
  // ---------------------------------------------------------------------------
  const MIN_BUDGET_PREMIUM = 1500000; // 1.5M EGP
  const BROKER_KEYWORDS = [
    "سمسار", "عقارات", "عندي عقارات", "مطور عقاري",
    "للبيع", "إعلان تجاري", "للإيجار", "أجار",
    "real estate", "broker", "developer", "rent",
  ];

  const PROPERTY_TYPES = {
    industrial: { label: "صناعي", score: 20 },
    commercial: { label: "تجاري", score: 20 },
    villa: { label: "فيلا", score: 15 },
    compound: { label: "كمبوند", score: 15 },
    duplex: { label: "دوبلكس", score: 12 },
    apartment: { label: "شقة", score: 8 },
    studio: { label: "استوديو", score: 5 },
    land: { label: "أرض", score: 18 },
  };

  const TIMELINE_MAP = {
    urgent: { label: "عاجل", score: 10 },
    flexible: { label: "مرن", score: 10 },
    exploring: { label: "استكشاف", score: 5 },
  };

  const AREA_BONUS = {
    sadat: { keywords: ["سادات", "مدينة السادات", "السادس", "المنطقة 7", "المنطقة 9", "المنطقة 15", "الشريط المميز"], score: 10 },
  };

  // ---------------------------------------------------------------------------
  // Text normalization
  // ---------------------------------------------------------------------------
  function normalize(text) {
    return text
      .replace(/[\u0610-\u061A]/g, "")
      .replace(/[\u064B-\u065F]/g, "")
      .replace(/[\u0670]/g, "")
      .replace(/\u0640/g, "")
      .toLowerCase();
  }

  // ---------------------------------------------------------------------------
  // Extract phone from text
  // ---------------------------------------------------------------------------
  function extractPhone(text) {
    const match = text.match(/(?:\+20|0020|0)?1[0125]\d{8}/);
    return match ? match[0] : null;
  }

  // ---------------------------------------------------------------------------
  // Extract property type
  // ---------------------------------------------------------------------------
  function detectPropertyType(text) {
    const lower = normalize(text);
    if (/شقة|شقتين|3 شقق|4 شقق/.test(lower)) return "apartment";
    if (/فيلا|فيلات/.test(lower)) return "villa";
    if (/دوبلكس|تريبل/.test(lower)) return "duplex";
    if (/استوديو/.test(lower)) return "studio";
    if (/كمبوند|compound/.test(lower)) return "compound";
    if (/محل|محلات|مكتب|مكاتب|تجاري/.test(lower)) return "commercial";
    if (/مصنع|مصانع|صناعي|فactory/.test(lower)) return "industrial";
    if (/أرض|ارض|land|plot/.test(lower)) return "land";
    if (/عمارة|.building/.test(lower)) return "apartment";
    return null;
  }

  // ---------------------------------------------------------------------------
  // Extract budget
  // ---------------------------------------------------------------------------
  function detectBudget(text) {
    const lower = normalize(text);
    const patterns = [
      { re: /(\d[\d,.]*)\s*(مليون|ملايين)/i, mul: 1000000 },
      { re: /(\d[\d,.]*)\s*(ك|k)\b/i, mul: 1000 },
      { re: /(\d[\d,.]*)\s*(جنيه|ج\.م|egp)/i, mul: 1 },
      { re: /(\d[\d,.]*)\s*(الف|ألف)/i, mul: 1000 },
    ];
    for (const { re, mul } of patterns) {
      const m = lower.match(re);
      if (m) {
        return parseFloat(m[1].replace(/[,.\s]/g, "")) * mul;
      }
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // Extract area/neighborhood
  // ---------------------------------------------------------------------------
  function detectArea(text) {
    const lower = normalize(text);
    const areas = [
      "المنطقة 7", "المنطقة 9", "المنطقة 15", "الشريط المميز",
      "المنطقة الصناعية", "المنطقة الحرة",
      "مدينة السادات", "سادات", "السادس",
    ];
    for (const area of areas) {
      if (lower.includes(normalize(area))) return area;
    }
    // Broader Egypt
    const broader = [
      "القاهرة", "الجيزة", "الإسكندرية", "أكتوبر", "6 أكتوبر",
      "مصر الجديدة", "مدينة نصر", "المعادي", "الزمالك",
      "الشروق", "العبور", "بدر",
    ];
    for (const area of broader) {
      if (lower.includes(normalize(area))) return area;
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // Detect timeline
  // ---------------------------------------------------------------------------
  function detectTimeline(text) {
    const lower = normalize(text);
    if (/عاجل|فورا|حالا|urgent|asap|dali/.test(lower)) return "urgent";
    if (/مرن|flexible|مش ه rushed|مش م rush/.test(lower)) return "flexible";
    if (/أدور|ببحث|بستكشف|exploring|looking/.test(lower)) return "exploring";
    return "flexible"; // default
  }

  // ---------------------------------------------------------------------------
  // Detect bedrooms
  // ---------------------------------------------------------------------------
  function detectBedrooms(text) {
    const lower = normalize(text);
    if (/استوديو/.test(lower)) return 0;
    if (/غرفتين|2 غرف|2 غرفة/.test(lower)) return 2;
    if (/3 غرف|3 غرفة|ثلاث/.test(lower)) return 3;
    if (/4 غرف|4 غرفة|اربع/.test(lower)) return 4;
    if (/5 غرف|5 غرفة|خمس/.test(lower)) return 5;
    return null;
  }

  // ---------------------------------------------------------------------------
  // Detect broker
  // ---------------------------------------------------------------------------
  function isBroker(text) {
    const lower = normalize(text);
    return BROKER_KEYWORDS.some((kw) => lower.includes(normalize(kw)));
  }

  // ---------------------------------------------------------------------------
  // Detect seriousness
  // ---------------------------------------------------------------------------
  function detectSeriousness(text) {
    const lower = normalize(text);
    const serious = [
      /عايز أشتري/, /عايز أبيع/, /بشتري/, /عايز شراء/,
      /عايز استثمر/, /ميزانيتي\s*\d/,
      /أقدر أدفع/, /بدي/, /محتاج/,
      /looking for/, /want to buy/, /budget/,
    ];
    return serious.some((re) => re.test(lower));
  }

  // ---------------------------------------------------------------------------
  // MAIN: Score a lead
  // ---------------------------------------------------------------------------
  function scoreLead({ text, senderName, source, phone }) {
    if (!text) return { score: 0, tier: "rejected", breakdown: {} };

    const breakdown = {};
    let total = 0;

    // 1. Broker check (auto-reject)
    if (isBroker(text)) {
      return {
        score: 0,
        tier: "rejected",
        breakdown: { broker: -30 },
        reasons: ["Seller/broker detected — auto-rejected"],
        propertyType: null,
        budget: null,
        area: null,
        timeline: null,
        phone: extractPhone(text),
      };
    }

    // 2. Property type scoring
    const propertyType = detectPropertyType(text);
    if (propertyType && PROPERTY_TYPES[propertyType]) {
      const pts = PROPERTY_TYPES[propertyType].score;
      breakdown.property_type = pts;
      total += pts;
    }

    // 3. Budget scoring
    const budget = detectBudget(text);
    if (budget !== null) {
      if (budget >= 3000000) { breakdown.budget = 35; total += 35; }
      else if (budget >= 1500000) { breakdown.budget = 25; total += 25; }
      else if (budget >= 500000) { breakdown.budget = 15; total += 15; }
      else { breakdown.budget = 8; total += 8; }
    }

    // 4. Timeline scoring
    const timeline = detectTimeline(text);
    if (timeline && TIMELINE_MAP[timeline]) {
      breakdown.timeline = TIMELINE_MAP[timeline].score;
      total += TIMELINE_MAP[timeline].score;
    }

    // 5. Area scoring (El Sadat bonus)
    const area = detectArea(text);
    if (area) {
      const isSadat = AREA_BONUS.sadat.keywords.some((kw) =>
        normalize(area).includes(normalize(kw))
      );
      if (isSadat) {
        breakdown.area = AREA_BONUS.sadat.score;
        total += AREA_BONUS.sadat.score;
      }
    }

    // 6. Seriousness scoring
    if (detectSeriousness(text)) {
      breakdown.seriousness = 10;
      total += 10;
    }

    // 7. WhatsApp origin bonus
    if (source === "whatsapp") {
      breakdown.origin = 10;
      total += 10;
    }

    // 8. Phone presence bonus
    const detectedPhone = phone || extractPhone(text);
    if (detectedPhone) {
      breakdown.contact = 5;
      total += 5;
    }

    // Cap at 100
    total = Math.min(total, 100);

    // Determine tier
    let tier;
    if (total >= 80) tier = "platinum";
    else if (total >= 60) tier = "gold";
    else if (total >= 40) tier = "silver";
    else tier = "rejected";

    // Build reasons
    const reasons = [];
    if (propertyType) reasons.push(`Property type: ${PROPERTY_TYPES[propertyType].label}`);
    if (budget) reasons.push(`Budget: ${(budget / 1000).toFixed(0)}K EGP`);
    if (area) reasons.push(`Area: ${area}`);
    if (timeline) reasons.push(`Timeline: ${TIMELINE_MAP[timeline].label}`);
    if (source === "whatsapp") reasons.push("WhatsApp lead (+10)");
    if (detectedPhone) reasons.push("Phone provided (+5)");

    return {
      score: total,
      tier,
      breakdown,
      reasons,
      propertyType,
      budget,
      area,
      bedrooms: detectBedrooms(text),
      timeline,
      phone: detectedPhone,
    };
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    scoreLead,
    extractPhone,
    detectPropertyType,
    detectBudget,
    detectArea,
    detectTimeline,
    detectBedrooms,
    isBroker,
    normalize,
    PROPERTY_TYPES,
    TIMELINE_MAP,
    MIN_BUDGET_PREMIUM,
  };
})();
