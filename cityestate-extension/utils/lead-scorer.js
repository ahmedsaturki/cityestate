/**
 * CityEstate — Lead Scoring Utility
 * ===================================
 * Heuristic + optional LLM lead scoring.
 * Score range: 0-100. Tiers: hot (>=70), warm (>=40), cold (<40).
 */

(function () {
  "use strict";

  const CityEstateLeadScorer = {
    // -------------------------------------------------------------------
    // Score a single lead using heuristics
    // -------------------------------------------------------------------
    scoreLead(lead) {
      let score = 30; // base
      const text = JSON.stringify(lead || {}).toLowerCase();

      // Contactability
      if (lead.phone && /^0?1[0125]\d{8}$/.test(lead.phone.replace(/\D/g, ""))) score += 20;
      if (lead.name) score += 5;

      // Intent detection
      if (/شراء|buy|عايز|interested|نفسي/.test(text)) score += 15;
      if (/بيع|sell/.test(text)) score += 5;
      if (/استثمار|invest/.test(text)) score += 10;
      if (/إيجار|ايجار|rent/.test(text)) score += 5;

      // Budget signals
      const budget = parseFloat(lead.budget) || 0;
      if (budget >= 5000000) score += 15;       // luxury
      else if (budget >= 2000000) score += 10;  // premium
      else if (budget >= 1000000) score += 5;   // mid

      // Property specifics
      if (lead.area) score += 5;
      if (lead.bedrooms) score += 5;

      // Urgency
      if (/مستعجل|عاجل|فوراً|قريباً|الآن/.test(text)) score += 10;

      // Recency boost
      if (lead.created_at) {
        const ageDays = (Date.now() - new Date(lead.created_at).getTime()) / 86400000;
        if (ageDays < 1) score += 10;
        else if (ageDays < 3) score += 5;
      }

      return Math.max(0, Math.min(100, score));
    },

    tier(score) {
      if (score >= 70) return "hot";
      if (score >= 40) return "warm";
      return "cold";
    },

    tierLabel(score) {
      return this.tier(score) === "hot" ? "🔥 ساخن"
        : this.tier(score) === "warm" ? "🟡 دافئ" : "❄️ بارد";
    },

    // -------------------------------------------------------------------
    // Score a batch of leads
    // -------------------------------------------------------------------
    scoreBatch(leads) {
      return (leads || []).map((lead) => {
        const score = this.scoreLead(lead);
        return { ...lead, score, tier: this.tier(score), tierLabel: this.tierLabel(score) };
      });
    },

    // -------------------------------------------------------------------
    // Simple matching between leads and properties
    // -------------------------------------------------------------------
    match(leads, properties) {
      const matches = [];
      for (const lead of (leads || []).slice(0, 50)) {
        for (const prop of (properties || []).slice(0, 50)) {
          let score = 0;
          // Area match
          const leadArea = (lead.area || "").toLowerCase();
          const propArea = (prop.area || "").toLowerCase();
          if (leadArea && propArea && (leadArea.includes(propArea) || propArea.includes(leadArea))) {
            score += 50;
          }
          // Budget match (within 20%)
          const lb = parseFloat(lead.budget) || 0;
          const pb = parseFloat(prop.price || prop.budget) || 0;
          if (lb && pb) {
            const diff = Math.abs(lb - pb) / lb;
            if (diff < 0.2) score += 30;
            else if (diff < 0.4) score += 15;
          }
          // Bedrooms
          if (lead.bedrooms && prop.bedrooms && lead.bedrooms === prop.bedrooms) score += 20;

          if (score >= 50) {
            matches.push({
              lead: lead.name || lead.phone || "عميل",
              leadPhone: lead.phone || "",
              property: prop.title || prop.area || "عقار",
              propertyId: prop.id || null,
              score,
            });
          }
        }
      }
      return matches.sort((a, b) => b.score - a.score).slice(0, 100);
    },
  };

  // Expose globally (content scripts) and for module use
  if (typeof window !== "undefined") window.CityEstateLeadScorer = CityEstateLeadScorer;
  if (typeof module !== "undefined") module.exports = CityEstateLeadScorer;
})();
