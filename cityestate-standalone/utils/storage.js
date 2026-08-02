/**
 * CityEstate Standalone — Chrome Storage Helper
 * ================================================
 * Simple wrapper around chrome.storage.local for leads, notes, and stats.
 */

window.CityEstateStorage = (function () {
  "use strict";

  const LEADS_KEY = "leads";
  const NOTES_KEY = "notes";
  const STATS_KEY = "stats";
  const SETTINGS_KEY = "settings";
  const MAX_LEADS = 500;
  const MAX_NOTES = 200;

  // ---------------------------------------------------------------------------
  // Generic helpers
  // ---------------------------------------------------------------------------
  async function get(key, defaultVal) {
    try {
      const result = await chrome.storage.local.get(key);
      return result[key] !== undefined ? result[key] : defaultVal;
    } catch (e) {
      console.warn("[Storage] get failed:", e);
      return defaultVal;
    }
  }

  async function set(key, value) {
    try {
      await chrome.storage.local.set({ [key]: value });
    } catch (e) {
      console.error("[Storage] set failed:", e);
    }
  }

  // ---------------------------------------------------------------------------
  // Leads
  // ---------------------------------------------------------------------------
  async function getLeads() {
    return (await get(LEADS_KEY, []));
  }

  async function addLead(lead) {
    const leads = await getLeads();
    // Dedup by chatId+text hash
    const hash = `${lead.chatId || ""}_${(lead.text || "").substring(0, 50)}`;
    if (leads.some((l) => l._hash === hash)) return false;

    lead._hash = hash;
    lead._ts = Date.now();
    leads.unshift(lead);

    // Trim to max
    if (leads.length > MAX_LEADS) leads.length = MAX_LEADS;

    await set(LEADS_KEY, leads);

    // Update stats
    const stats = await getStats();
    stats.totalLeads = leads.length;
    stats.leadsByTier[lead.tier || "unknown"] = (stats.leadsByTier[lead.tier || "unknown"] || 0) + 1;
    await set(STATS_KEY, stats);

    return true;
  }

  async function getLeadCount() {
    const leads = await getLeads();
    return leads.length;
  }

  async function getLeadsByTier(tier) {
    const leads = await getLeads();
    return leads.filter((l) => l.tier === tier);
  }

  // ---------------------------------------------------------------------------
  // Notes
  // ---------------------------------------------------------------------------
  async function getNotes() {
    return (await get(NOTES_KEY, []));
  }

  async function addNote(note) {
    const notes = await getNotes();
    note._ts = Date.now();
    note._id = `note_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    notes.unshift(note);

    if (notes.length > MAX_NOTES) notes.length = MAX_NOTES;

    await set(NOTES_KEY, notes);
    return note._id;
  }

  async function deleteNote(id) {
    const notes = await getNotes();
    const filtered = notes.filter((n) => n._id !== id);
    await set(NOTES_KEY, filtered);
  }

  // ---------------------------------------------------------------------------
  // Stats
  // ---------------------------------------------------------------------------
  async function getStats() {
    return (await get(STATS_KEY, {
      totalLeads: 0,
      leadsByTier: {},
      messagesProcessed: 0,
      autoReplies: 0,
      lastActivity: null,
    }));
  }

  async function incrementStat(field, amount = 1) {
    const stats = await getStats();
    stats[field] = (stats[field] || 0) + amount;
    stats.lastActivity = Date.now();
    await set(STATS_KEY, stats);
  }

  // ---------------------------------------------------------------------------
  // Settings
  // ---------------------------------------------------------------------------
  async function getSettings() {
    return (await get(SETTINGS_KEY, {
      autoReplyEnabled: true,
      showNotifications: true,
      scoreThreshold: 40,
    }));
  }

  async function updateSettings(partial) {
    const settings = await getSettings();
    Object.assign(settings, partial);
    await set(SETTINGS_KEY, settings);
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    getLeads,
    addLead,
    getLeadCount,
    getLeadsByTier,
    getNotes,
    addNote,
    deleteNote,
    getStats,
    incrementStat,
    getSettings,
    updateSettings,
  };
})();
