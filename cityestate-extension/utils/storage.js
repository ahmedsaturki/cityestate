/**
 * CityEstate — Storage Utility
 * ==============================
 * Centralized chrome.storage helpers with safe defaults.
 */

(function () {
  "use strict";

  const CityEstateStorage = {
    PREFIX: "ce_",

    async get(key, fallback = null) {
      const k = key.startsWith(this.PREFIX) ? key : this.PREFIX + key;
      const data = await chrome.storage.local.get(k);
      return data[k] !== undefined ? data[k] : fallback;
    },

    async set(key, value) {
      const k = key.startsWith(this.PREFIX) ? key : this.PREFIX + key;
      await chrome.storage.local.set({ [k]: value });
      return value;
    },

    async remove(key) {
      const k = key.startsWith(this.PREFIX) ? key : this.PREFIX + key;
      await chrome.storage.local.remove(k);
    },

    // -------------------------------------------------------------------
    // Domain helpers
    // -------------------------------------------------------------------
    async getLeads() {
      return (await this.get("leads")) || [];
    },

    async saveLeads(leads) {
      return this.set("leads", leads.slice(-200));
    },

    async addLead(lead) {
      const leads = await this.getLeads();
      leads.push({ ...lead, created_at: new Date().toISOString() });
      await this.saveLeads(leads);
      return lead;
    },

    async getActivity() {
      return (await this.get("activity")) || [];
    },

    async addActivity(text, icon = "📌") {
      const activities = await this.getActivity();
      activities.unshift({ text, icon, time: Date.now() });
      return this.set("activity", activities.slice(0, 50));
    },

    async getStats() {
      return {
        sent: (await this.get("messagesSent")) || 0,
        received: (await this.get("messagesReceived")) || 0,
        leads: (await this.getLeads()).length,
        scored: (await this.get("scoredLeads")) || [],
      };
    },

    async getSettings() {
      return (await this.get("settings")) || {
        serverUrl: "http://localhost:8000",
        operationMode: "bridge",
        speedLevel: "normal",
        autoReplyEnabled: true,
        notificationsEnabled: true,
      };
    },

    async saveSettings(settings) {
      return this.set("settings", settings);
    },
  };

  // Expose
  if (typeof window !== "undefined") window.CityEstateStorage = CityEstateStorage;
  if (typeof module !== "undefined") module.exports = CityEstateStorage;
})();
