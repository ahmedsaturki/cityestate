/**
 * CityEstate Standalone — El Sadat City Knowledge Base
 * ======================================================
 * Built-in data about El Sadat City for the extension.
 * No API needed — pure reference data.
 */

window.CityEstateKnowledge = (function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Area metadata
  // ---------------------------------------------------------------------------
  const AREAS = {
    "المنطقة 7": {
      name: "المنطقة 7 — الشريط المميز",
      description: "منطقة مميزة على الرئيسي، تجارية وسكنية",
      priceRange: { min: 1500000, max: 5000000 },
      avgPricePerSqm: 8000,
      highlights: ["شارع رئيسي", "قريبة من الخدمات", "موقع تجاري ممتاز"],
      propertyTypes: ["شقة", "دوبلكس", "محل تجاري"],
      investmentScore: 9,
    },
    "المنطقة 9": {
      name: "المنطقة 9",
      description: "منطقة سكنية هادئة مع خدمات متنوعة",
      priceRange: { min: 800000, max: 3000000 },
      avgPricePerSqm: 5500,
      highlights: ["هادئة", "قريبة من المدارس", "بنية تحتية جيدة"],
      propertyTypes: ["شقة", "فيلا", "دوبلكس"],
      investmentScore: 7,
    },
    "المنطقة 15": {
      name: "المنطقة 15",
      description: "منطقة نامية بفرص استثمارية",
      priceRange: { min: 600000, max: 2000000 },
      avgPricePerSqm: 4000,
      highlights: ["أسعار مناسبة", "نمو سريع", "قريبة من المنطقة الصناعية"],
      propertyTypes: ["شقة", "استوديو", "أرض"],
      investmentScore: 8,
    },
    "المنطقة الصناعية": {
      name: "المنطقة الصناعية",
      description: "-heart of El Sadat industrial zone — $7B exports",
      priceRange: { min: 1000000, max: 10000000 },
      avgPricePerSqm: 3000,
      highlights: ["تصدير 7 مليار دولار", "ميناء", "طرق سريعة", "بنية تحتية متطورة"],
      propertyTypes: ["مصنع", "أرض صناعية", "مستودع"],
      investmentScore: 10,
    },
    "المنطقة الحرة": {
      name: "المنطقة الحرة — Free Zone",
      description: "منطقة حرة للتصدير والاستيراد",
      priceRange: { min: 2000000, max: 15000000 },
      avgPricePerSqm: 5000,
      highlights: ["إعفاء ضريبي", "تصدير مباشر", "قرب من الميناء"],
      propertyTypes: ["مصنع", "مستودع", "مكتب"],
      investmentScore: 10,
    },
  };

  // ---------------------------------------------------------------------------
  // City overview
  // ---------------------------------------------------------------------------
  const CITY = {
    name: "مدينة السادات",
    nameEn: "El Sadat City",
    governorate: "المنوفية",
    distanceFromCairo: "90km",
    distanceFromAlexandria: "60km",
    area: "121,000 فدان",
    population: "~500,000",
    exports: "$7B سنوياً",
    keyIndustries: ["غزل ونسيج", "صناعات غذائية", "هندسية", "إلكترونية"],
    landmarks: ["جامعة السادات", "المستشفى التعليمي", "ال:ministerial district"],
    transportation: ["طريق Cairo-Alexandria السريع", "قريب من مطار برج العرب"],
    advantages: [
      "بنية تحتية متطورة",
      "قرب من القاهرة والإسكندرية",
      "منطقة صناعية قوية",
      "أسعار أقل من القاهرة بـ 50-70%",
      "نمو سكاني سريع",
      "خدمات متكاملة (تعليم، صحة، ترفيه)",
    ],
  };

  // ---------------------------------------------------------------------------
  // Property comparison data
  // ---------------------------------------------------------------------------
  const MARKET_DATA = {
    "شقة": {
      avgPrice: 900000,
      pricePerSqm: 5500,
      typicalArea: "80-150 م²",
      rentalYield: "8-12%",
    },
    "فيلا": {
      avgPrice: 2500000,
      pricePerSqm: 7000,
      typicalArea: "200-400 م²",
      rentalYield: "5-8%",
    },
    "دوبلكس": {
      avgPrice: 1800000,
      pricePerSqm: 6000,
      typicalArea: "180-300 م²",
      rentalYield: "7-10%",
    },
    "محل تجاري": {
      avgPrice: 1500000,
      pricePerSqm: 8000,
      typicalArea: "50-200 م²",
      rentalYield: "12-18%",
    },
    "أرض": {
      avgPrice: 500000,
      pricePerSqm: 2000,
      typicalArea: "200-1000 م²",
      rentalYield: "N/A (استثمار)",
    },
    "مصنع": {
      avgPrice: 5000000,
      pricePerSqm: 3000,
      typicalArea: "500-5000 م²",
      rentalYield: "10-15%",
    },
  };

  // ---------------------------------------------------------------------------
  // Premium filtering: is this a premium property?
  // ---------------------------------------------------------------------------
  function isPremium(data) {
    if (!data) return false;
    const budget = data.budget || 0;
    const type = data.propertyType || "";
    // Premium: budget >= 1.5M OR type is industrial/commercial/villa/land
    if (budget >= 1500000) return true;
    if (["industrial", "commercial", "villa", "land"].includes(type)) return true;
    return false;
  }

  // ---------------------------------------------------------------------------
  // Get area info
  // ---------------------------------------------------------------------------
  function getAreaInfo(areaName) {
    if (!areaName) return null;
    for (const [key, data] of Object.entries(AREAS)) {
      if (areaName.includes(key) || key.includes(areaName)) return data;
    }
    return null;
  }

  // ---------------------------------------------------------------------------
  // Get property type info
  // ---------------------------------------------------------------------------
  function getPropertyInfo(type) {
    return MARKET_DATA[type] || null;
  }

  // ---------------------------------------------------------------------------
  // Get city overview
  // ---------------------------------------------------------------------------
  function getCityInfo() {
    return CITY;
  }

  // ---------------------------------------------------------------------------
  // Calculate price per sqm
  // ---------------------------------------------------------------------------
  function calcPricePerSqm(price, sqm) {
    if (!price || !sqm || sqm === 0) return null;
    return Math.round(price / sqm);
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    AREAS,
    CITY,
    MARKET_DATA,
    isPremium,
    getAreaInfo,
    getPropertyInfo,
    getCityInfo,
    calcPricePerSqm,
  };
})();
