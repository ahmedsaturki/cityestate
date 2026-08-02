/**
 * CityEstate Bridge — DOM Observer Utility
 * ===========================================
 * Generic DOM mutation observer for monitoring page changes.
 * Used by Facebook content script to detect new posts.
 */

window.CityEstateDOMObserver = (function () {
  "use strict";

  /**
   * Create a debounced mutation observer
   * @param {HTMLElement} target - Element to observe
   * @param {Function} callback - Callback when changes detected
   * @param {Object} options - Observer options
   * @returns {MutationObserver}
   */
  function create(target, callback, options = {}) {
    const debounceMs = options.debounceMs || 300;
    let debounceTimer = null;

    const observer = new MutationObserver((mutations) => {
      if (debounceTimer) return;

      debounceTimer = setTimeout(() => {
        debounceTimer = null;
        callback(mutations);
      }, debounceMs);
    });

    observer.observe(target, {
      childList: options.childList !== false,
      subtree: options.subtree !== false,
      characterData: options.characterData !== false,
      attributes: options.attributes || false,
    });

    return observer;
  }

  /**
   * Wait for an element to appear in the DOM
   * @param {string} selector - CSS selector
   * @param {number} timeout - Timeout in ms
   * @returns {Promise<Element>}
   */
  function waitForElement(selector, timeout = 10000) {
    return new Promise((resolve, reject) => {
      const existing = document.querySelector(selector);
      if (existing) {
        resolve(existing);
        return;
      }

      const observer = new MutationObserver(() => {
        const el = document.querySelector(selector);
        if (el) {
          observer.disconnect();
          resolve(el);
        }
      });

      observer.observe(document.body, {
        childList: true,
        subtree: true,
      });

      setTimeout(() => {
        observer.disconnect();
        reject(new Error(`Timeout waiting for ${selector}`));
      }, timeout);
    });
  }

  /**
   * Get all text content from an element
   * @param {Element} element
   * @returns {string}
   */
  function getTextContent(element) {
    if (!element) return "";
    return element.textContent.trim();
  }

  /**
   * Check if element is visible in viewport
   * @param {Element} element
   * @returns {boolean}
   */
  function isVisible(element) {
    if (!element) return false;
    const rect = element.getBoundingClientRect();
    return (
      rect.top >= 0 &&
      rect.left >= 0 &&
      rect.bottom <= window.innerHeight &&
      rect.right <= window.innerWidth
    );
  }

  return {
    create,
    waitForElement,
    getTextContent,
    isVisible,
  };
})();
