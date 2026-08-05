"""Facebook-specific automation (Phase 5 — Meta API cleanup).

FacebookExpert was removed during the Phase 5 Meta API cleanup.
This stub preserves backward compatibility for any code that still
imports ``FacebookExpert`` from ``src.automation.experts``.
"""

import logging

logger = logging.getLogger("cityestate.automation.facebook")


class FacebookExpert:
    """Placeholder — Facebook automation removed in Phase 5.

    All methods raise ``NotImplementedError`` with a clear message.
    """

    def __init__(self, *args, **kwargs):
        logger.warning(
            "FacebookExpert is a stub (Phase 5 removal). "
            "Facebook automation is not available."
        )

    def scrape_group(self, *args, **kwargs):
        raise NotImplementedError(
            "FacebookExpert was removed in Phase 5. "
            "Use the browser automation layer directly for Facebook scraping."
        )

    def extract_leads(self, *args, **kwargs):
        raise NotImplementedError(
            "FacebookExpert was removed in Phase 5. "
            "Use the browser automation layer directly for Facebook scraping."
        )

    def monitor_group(self, *args, **kwargs):
        raise NotImplementedError(
            "FacebookExpert was removed in Phase 5. "
            "Use the browser automation layer directly for Facebook scraping."
        )
