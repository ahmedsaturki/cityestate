/**
 * CityEstate Bridge — Typewriter Engine
 * ========================================
 * Human-like typing engine that makes automated messages
 * appear as if typed by a real person.
 *
 * Features:
 * - Random delay between characters: 50-150ms
 * - Occasional typos (3% chance) + backspace correction
 * - Thinking pauses: 500-2000ms mid-sentence
 * - Variable typing speed based on message length
 * - Never types exactly the same way twice
 */

window.CityEstateTypewriter = (function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Configuration
  // ---------------------------------------------------------------------------
  const CONFIG = {
    minCharDelay: 40,     // Minimum ms per character
    maxCharDelay: 180,    // Maximum ms per character
    typoChance: 0.03,     // 3% chance of typo per character
    thinkingPauseChance: 0.08,  // 8% chance of thinking pause
    thinkingPauseMin: 400,      // Minimum thinking pause ms
    thinkingPauseMax: 2000,     // Maximum thinking pause ms
    periodPauseChance: 0.15,    // 15% chance of pause after period
    periodPauseMin: 300,
    periodPauseMax: 800,
    emojiDelay: 50,       // Extra delay before emoji
  };

  // English keyboard neighbors for realistic typos
  const ENGLISH_NEIGHBORS = {
    "a": ["s", "q", "z"], "b": ["v", "g", "h"], "c": ["x", "d", "f"],
    "d": ["s", "f", "e"], "e": ["w", "r", "d"], "f": ["d", "g", "r"],
    "g": ["f", "h", "t"], "h": ["g", "j", "y"], "i": ["u", "o", "k"],
    "j": ["h", "k", "u"], "k": ["j", "l", "i"], "l": ["k", "o"],
    "m": ["n", "j"], "n": ["m", "b", "h"], "o": ["i", "p", "l"],
    "p": ["o"], "q": ["w", "a"], "r": ["e", "t", "f"],
    "s": ["a", "d", "w"], "t": ["r", "y", "g"], "u": ["y", "i", "j"],
    "v": ["c", "b", "f"], "w": ["q", "e", "s"], "x": ["z", "c", "d"],
    "y": ["t", "u", "h"], "z": ["x", "a"],
  };

  // Arabic keyboard layout for realistic typos
  const ARABIC_NEIGHBORS = {
    "ا": ["ب", "ل", "م"],
    "ب": ["ا", "ت", "ن"],
    "ت": ["ب", "ث", "ي"],
    "ث": ["ت", "ج", "ي"],
    "ج": ["ث", "ح", "د"],
    "ح": ["ج", "خ", "ذ"],
    "خ": ["ح", "د", "ش"],
    "د": ["خ", "ذ", "ر"],
    "ذ": ["د", "ر", "ز"],
    "ر": ["ذ", "ز", "س"],
    "ز": ["ر", "س", "ص"],
    "س": ["ز", "ش", "ص"],
    "ش": ["س", "ص", "ض"],
    "ص": ["ش", "ض", "ط"],
    "ض": ["ص", "ط", "ظ"],
    "ط": ["ض", "ظ", "ع"],
    "ظ": ["ط", "ع", "غ"],
    "ع": ["ظ", "غ", "ف"],
    "غ": ["ع", "ف", "ق"],
    "ف": ["غ", "ق", "ك"],
    "ق": ["ف", "ك", "ل"],
    "ك": ["ق", "ل", "م"],
    "ل": ["ك", "م", "ن"],
    "م": ["ل", "ن", "ه"],
    "ن": ["م", "ه", "و"],
    "ه": ["ن", "و", "ي"],
    "و": ["ه", "ي", "ء"],
    "ي": ["و", "ء", "ا"],
  };

  // ---------------------------------------------------------------------------
  // Typing Engine
  // ---------------------------------------------------------------------------
  function type(element, text) {
    return new Promise((resolve) => {
      if (!element || !text) {
        resolve(false);
        return;
      }

      // Clear existing content
      element.focus();
      document.execCommand("selectAll", false, null);
      document.execCommand("delete", false, null);

      let charIndex = 0;
      const chars = [...text]; // Support Unicode/emojis

      function typeNextChar() {
        if (charIndex >= chars.length) {
          resolve(true);
          return;
        }

        const char = chars[charIndex];
        const isEmoji = /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}]/u.test(char);
        const isPeriod = char === "." || char === "!" || char === "?" || char === "،";

        // Random thinking pause
        if (Math.random() < CONFIG.thinkingPauseChance && charIndex > 0) {
          const pause = randomBetween(CONFIG.thinkingPauseMin, CONFIG.thinkingPauseMax);
          setTimeout(() => insertChar(char), pause);
          return;
        }

        // Period pause
        if (isPeriod && Math.random() < CONFIG.periodPauseChance) {
          const pause = randomBetween(CONFIG.periodPauseMin, CONFIG.periodPauseMax);
          setTimeout(() => insertChar(char), pause);
          return;
        }

        // Emoji delay
        if (isEmoji) {
          setTimeout(() => insertChar(char), CONFIG.emojiDelay);
          return;
        }

        // Normal character delay
        const delay = randomBetween(CONFIG.minCharDelay, CONFIG.maxCharDelay);
        setTimeout(() => insertChar(char), delay);
      }

      function insertChar(char) {
        // Chance of typo (Arabic or English)
        const neighbors = ARABIC_NEIGHBORS[char] || ENGLISH_NEIGHBORS[char.toLowerCase()];
        if (Math.random() < CONFIG.typoChance && neighbors) {
          let typoChar = neighbors[Math.floor(Math.random() * neighbors.length)];
          // Preserve case for English
          if (char === char.toUpperCase() && char !== char.toLowerCase()) {
            typoChar = typoChar.toUpperCase();
          }

          // Type the wrong character
          document.execCommand("insertText", false, typoChar);

          // Pause before correcting
          setTimeout(() => {
            // Backspace to delete wrong char
            document.execCommand("delete", false, null);

            // Type correct character
            setTimeout(() => {
              document.execCommand("insertText", false, char);
              charIndex++;
              typeNextChar();
            }, randomBetween(50, 150));
          }, randomBetween(100, 300));

          return;
        }

        // Normal character insertion
        document.execCommand("insertText", false, char);
        charIndex++;
        typeNextChar();
      }

      typeNextChar();
    });
  }

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------
  function randomBetween(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }

  function simulateTyping(text) {
    // Calculate total typing time estimate
    const charCount = text.length;
    const avgDelay = (CONFIG.minCharDelay + CONFIG.maxCharDelay) / 2;
    const estimatedTime = charCount * avgDelay;
    return {
      text,
      estimatedTime,
      characterCount: charCount,
    };
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    type,
    simulateTyping,
    CONFIG,
  };
})();
