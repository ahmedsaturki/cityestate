"""
WhatsApp Web Automation Service
Browser-based WhatsApp automation using Playwright
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# WhatsApp Web selectors (updated for current WhatsApp Web UI)
SELECTORS = {
    # Authentication
    "qr_code": "div[data-ref]",
    "qr_canvas": "canvas",
    
    # Search and navigation - CORRECT SELECTORS
    "search_box": "div[data-testid='chat-list-search-container'] div[contenteditable='true']",
    "search_container": "div[data-testid='chat-list-search-container']",
    "new_chat_button": "div[data-testid='new-chat-outline']",
    
    # Chat list - CORRECT SELECTORS
    "chat_list": "div[data-testid='cell-frame-container']",
    "chat_item": "div[data-testid='cell-frame-container']",
    "chat_name": "div[data-testid='cell-frame-title'] span[title]",
    "chat_last_message": "div[data-testid='last-msg-status']",
    "chat_unread": "span[data-testid='icon-unread-count']",
    
    # Message area
    "message_box": "div[contenteditable='true'][data-tab='10']",
    "message_box_footer": "footer",
    "send_button": "span[data-icon='send']",
    "attach_button": "span[data-icon='plus']",
    "emoji_button": "span[data-icon='smiley']",
    "voice_button": "span[data-icon='mic']",
    
    # Messages
    "message_bubble": "div.message-in, div.message-out",
    "message_text": "span.selectable-text",
    "message_time": "span[data-testid='msg-time']",
    
    # Navigation
    "menu_button": "div[role='button'][title='Menu']",
    "settings": "div[role='menuitem']",
    "profile_photo": "img[alt]",
    
    # Main screen
    "main_screen": "div[data-testid='wa-web-main-screen']",
    "chat_panel": "div[data-testid='chat-list']",
    
    # Tabs
    "unread_tab": "div[role='tab'] span[title='Unread']",
    "favourites_tab": "div[role='tab'] span[title='Favourites']",
    "groups_tab": "div[role='tab'] span[title='Groups']",
}


@dataclass
class WhatsAppMessage:
    """WhatsApp message data class"""
    id: str
    from_number: str
    to_number: str
    body: str
    timestamp: datetime
    is_from_me: bool
    message_type: str = "text"
    media_url: str | None = None


@dataclass
class WhatsAppChat:
    """WhatsApp chat data class"""
    id: str
    name: str
    phone: str
    last_message: str
    timestamp: datetime
    unread_count: int
    is_group: bool = False


class WhatsAppWeb:
    """WhatsApp Web automation using Playwright"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.page = None
        self.is_authenticated = False
        self.is_running = False
        self.session_dir = Path("whatsapp_session")
        self.session_dir.mkdir(exist_ok=True)
        
    async def start(self, headless: bool | None = None) -> bool:
        """Start WhatsApp Web automation (non-blocking)"""
        try:
            from playwright.async_api import async_playwright
            
            if headless is not None:
                self.headless = headless
            
            self.playwright = await async_playwright().start()
            
            # Launch browser with persistent context for session
            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.session_dir),
                headless=self.headless,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            self.page = self.browser.pages[0] if self.browser.pages else await self.browser.new_page()
            
            # Navigate to WhatsApp Web
            await self.page.goto("https://web.whatsapp.com", wait_until="networkidle")
            
            self.is_running = True
            
            # Check if already authenticated (session restored)
            await self._check_auth()
            
            if self.is_authenticated:
                logger.info("WhatsApp Web started - session restored")
            else:
                logger.info("WhatsApp Web started - waiting for QR code scan")
            
            return True
            
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False
        except Exception as e:
            logger.error(f"Failed to start WhatsApp Web: {e}")
            return False
    
    async def _check_auth(self) -> bool:
        """Quick check if already authenticated"""
        try:
            for selector in ["div[data-testid='wa-web-main-screen']", 
                           "div[data-testid='chat-list-search-container']",
                           "div[data-testid='cell-frame-container']"]:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    self.is_authenticated = True
                    return True
                except Exception as e:
                    logger.debug("WhatsApp auth check error: %s", e)
                    continue
            self.is_authenticated = False
            return False
        except Exception:
            self.is_authenticated = False
            return False
    
    async def check_and_update_auth(self) -> bool:
        """Check authentication status and update state (for polling)"""
        if not self.is_running or not self.page:
            self.is_authenticated = False
            return False
        
        return await self._check_auth()
    
    async def _wait_for_authentication(self, timeout: int = 60) -> bool:
        """Wait for QR code scan or session restoration"""
        try:
            # Check if already authenticated - look for search box or chat list
            for selector in [SELECTORS["search_box"], SELECTORS["chat_list"], "div[data-testid='chat-list']"]:
                try:
                    await self.page.wait_for_selector(
                        selector,
                        timeout=3000
                    )
                    self.is_authenticated = True
                    logger.info("Session restored - already authenticated")
                    return True
                except Exception as e:
                    logger.debug("WhatsApp session restore error: %s", e)
                    continue
            
            # Wait for QR code
            logger.info("Waiting for QR code scan...")
            qr_element = await self.page.wait_for_selector(
                SELECTORS["qr_code"],
                timeout=timeout * 1000
            )
            
            if qr_element:
                # Save QR code screenshot for user
                await self.page.screenshot(
                    path=str(self.session_dir / "qr_code.png"),
                    full_page=False
                )
                logger.info("QR code saved to whatsapp_session/qr_code.png")
                
                # Wait for authentication after QR scan
                await self.page.wait_for_selector(
                    SELECTORS["search_box"],
                    timeout=120000  # 2 minutes to scan
                )
                self.is_authenticated = True
                logger.info("Authenticated successfully")
                return True
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def send_message(self, phone: str, message: str) -> bool:
        """Send a text message to a phone number"""
        if not self.is_authenticated:
            logger.error("Not authenticated")
            return False
        
        try:
            # Format phone number (keep + for international format)
            phone = phone.replace(" ", "").replace("-", "")
            if not phone.startswith("+"):
                phone = "+" + phone
            
            logger.info(f"Sending message to {phone}")
            
            # Step 0: Close any popups/banners
            await self._dismiss_popups()
            
            # Step 1: Try to find contact in existing chat list first (avoids restriction)
            clicked = await self._click_chat_from_list(phone)
            
            # Step 2: If not found in list, use search (may trigger restriction)
            if not clicked:
                clicked = await self._click_chat_from_search(phone)
            
            if not clicked:
                logger.error(f"Could not find or open chat for {phone}")
                await self.take_screenshot("send_error.png")
                return False
            
            await asyncio.sleep(2)
            
            # Step 3: Check if message input is available (restriction may block it)
            msg_box = await self._find_message_box()
            if not msg_box:
                # Try to dismiss restriction banner
                await self._dismiss_popups()
                await asyncio.sleep(1)
                msg_box = await self._find_message_box()
            
            if not msg_box:
                logger.error("Message input box not found (possibly restricted)")
                await self.take_screenshot("send_restricted.png")
                return False
            
            # Step 4: Type message
            await msg_box.click()
            await asyncio.sleep(0.3)
            await self.page.keyboard.type(message, delay=30)
            await asyncio.sleep(0.5)
            
            # Step 5: Send
            send_btn = await self.page.query_selector("span[data-icon='send']")
            if send_btn:
                await send_btn.click()
            else:
                await self.page.keyboard.press("Enter")
            
            await asyncio.sleep(2)
            await self.take_screenshot("send_sent.png")
            
            logger.info(f"Message sent to {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {phone}: {e}")
            await self.take_screenshot("send_error.png")
            return False
    
    async def _dismiss_popups(self):
        """Close any popups, modals, or banners that block interaction"""
        try:
            # Use JavaScript to click all close/X buttons on popups
            await self.page.evaluate('''() => {
                // Close "Calling on web" popup
                const dialogs = document.querySelectorAll('[role="dialog"], [data-testid="popup-controls"]');
                dialogs.forEach(d => {
                    const closeBtn = d.querySelector('span[data-icon="x"], span[data-icon="x-outline"], div[role="button"]');
                    if (closeBtn) closeBtn.click();
                });
                
                // Close any visible X buttons
                document.querySelectorAll('span[data-icon="x"], span[data-icon="x-outline"]').forEach(el => {
                    if (el.offsetParent !== null) el.click();
                });
                
                // Dismiss restriction banner if present
                document.querySelectorAll('div[data-testid="chat-butterbar"] div[role="button"]').forEach(el => {
                    if (el.offsetParent !== null) el.click();
                });
            }''')
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.debug(f"Popup dismiss error: {e}")
    
    async def _click_chat_from_list(self, phone: str) -> bool:
        """Try to find and click an existing chat from the main chat list"""
        try:
            # Clear search first if active
            clear_btn = await self.page.query_selector("span[data-icon='x']")
            if clear_btn and await clear_btn.is_visible():
                await clear_btn.click()
                await asyncio.sleep(0.5)
            
            chat_items = await self.page.query_selector_all("div[data-testid='cell-frame-container']")
            logger.info(f"Found {len(chat_items)} chats in list")
            for item in chat_items:
                try:
                    text = await item.inner_text()
                    if phone in text or phone.lstrip("+") in text:
                        await item.click()
                        logger.info(f"Found and clicked chat from list: {phone}")
                    return True
                except Exception as e:
                    logger.debug("WhatsApp chat list error: %s", e)
                    continue
        except Exception as e:
            logger.debug(f"Could not find chat in list: {e}")
        return False
    
    async def _click_chat_from_search(self, phone: str) -> bool:
        """Use search to find and click a chat"""
        try:
            # Click search container
            search_container = await self.page.wait_for_selector(
                "div[data-testid='chat-list-search-container']",
                timeout=5000
            )
            await search_container.click()
            await asyncio.sleep(1)
            
            # Type phone number
            await self.page.keyboard.type(phone, delay=50)
            await asyncio.sleep(3)
            
            # Click first result
            chat_item = await self.page.wait_for_selector(
                "div[data-testid='cell-frame-container']",
                timeout=10000
            )
            await chat_item.click()
            logger.info(f"Clicked chat from search: {phone}")
            return True
        except Exception as e:
            logger.debug(f"Search failed: {e}")
            return False
    
    async def _find_message_box(self):
        """Find the message input box, trying multiple selectors"""
        selectors = [
            "footer div[contenteditable='true']",
            "div[contenteditable='true'][data-tab='10']",
            "div[role='textbox'][contenteditable='true']",
            "#main footer div[contenteditable]",
            "div.copyable-text[contenteditable='true']",
            "div[data-testid='conversation-compose-box-input']",
        ]
        for sel in selectors:
            try:
                el = await self.page.query_selector(sel)
                if el:
                    # Check if visible via JS
                    visible = await el.evaluate('el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; }')
                    if visible:
                        return el
            except Exception as e:
                logger.debug("WhatsApp element visibility error: %s", e)
                continue
        
        # Last resort: find any visible contenteditable in the main area
        try:
            all_editables = await self.page.query_selector_all("[contenteditable='true']")
            for el in all_editables:
                try:
                    visible = await el.evaluate('el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.bottom > window.innerHeight * 0.7; }')
                    if visible:
                        return el
                except Exception as e:
                    logger.debug("WhatsApp editable element error: %s", e)
                    continue
        except Exception as e:
            logger.debug("WhatsApp search error: %s", e)
        
        return None
    
    async def send_image(self, phone: str, image_path: str, caption: str = "") -> bool:
        """Send an image with optional caption"""
        if not self.is_authenticated:
            return False
        
        try:
            phone = phone.replace("+", "").replace(" ", "").replace("-", "")
            
            # Navigate to chat
            search_box = await self.page.wait_for_selector(
                SELECTORS["search_box"],
                timeout=10000
            )
            await search_box.click()
            await self.page.keyboard.press("Control+a")
            await self.page.keyboard.type(phone, delay=50)
            await asyncio.sleep(2)
            
            # Click on chat
            try:
                chat_item = await self.page.wait_for_selector(
                    f"div[role='listitem'] span[title='{phone}']",
                    timeout=5000
                )
                await chat_item.click()
            except Exception:
                first_result = await self.page.wait_for_selector(
                    SELECTORS["chat_list"],
                    timeout=5000
                )
                await first_result.click()
            
            await asyncio.sleep(1)
            
            # Click attach button
            attach_button = await self.page.wait_for_selector(
                SELECTORS["attach_button"],
                timeout=5000
            )
            await attach_button.click()
            
            await asyncio.sleep(0.5)
            
            # Click images & videos
            images_option = await self.page.wait_for_selector(
                "div[role='menuitem'][title='Photos & Videos']",
                timeout=5000
            )
            await images_option.click()
            
            # Upload image
            file_input = await self.page.wait_for_selector(
                "input[type='file'][accept='image/*,video/*']",
                timeout=5000
            )
            await file_input.set_input_files(image_path)
            
            await asyncio.sleep(2)
            
            # Add caption if provided
            if caption:
                caption_box = await self.page.wait_for_selector(
                    SELECTORS["message_box"],
                    timeout=5000
                )
                await caption_box.click()
                await self.page.keyboard.type(caption, delay=30)
            
            # Click send
            send_button = await self.page.wait_for_selector(
                SELECTORS["send_button"],
                timeout=5000
            )
            await send_button.click()
            
            await asyncio.sleep(1)
            
            logger.info(f"Image sent to {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send image to {phone}: {e}")
            return False
    
    async def get_unread_messages(self) -> list[dict[str, Any]]:
        """Get all unread messages"""
        if not self.is_authenticated:
            logger.error("Not authenticated")
            return []
        
        try:
            unread_messages = []
            
            # Take screenshot for debugging
            await self.take_screenshot("get_unread.png")
            
            # Find all chat items using the correct selector
            chat_items = await self.page.query_selector_all(
                SELECTORS["chat_list"]
            )
            
            logger.info(f"Found {len(chat_items)} chat items")
            
            for chat_item in chat_items:
                try:
                    # Get chat name
                    name_element = await chat_item.query_selector("span[title]")
                    name = await name_element.get_attribute("title") if name_element else "Unknown"
                    
                    # Skip if name is from tabs
                    if name in ["All", "Favourites", "Unread", "Groups"]:
                        continue
                    
                    # Get unread badge
                    unread_count = 0
                    try:
                        unread_badge = await chat_item.query_selector("span[data-testid='icon-unread-count']")
                        if unread_badge:
                            unread_text = await unread_badge.inner_text()
                            if unread_text.isdigit():
                                unread_count = int(unread_text)
                    except Exception as e:
                        logger.debug("WhatsApp unread badge error: %s", e)
                    
                    if unread_count > 0:
                        # Get last message preview
                        last_message = ""
                        try:
                            last_msg_element = await chat_item.query_selector("div[data-testid='last-msg-status']")
                            if last_msg_element:
                                last_message = await last_msg_element.inner_text()
                        except Exception as e:
                            logger.debug("WhatsApp last message error: %s", e)
                        
                        unread_messages.append({
                            "name": name,
                            "unread_count": unread_count,
                            "last_message": last_message,
                            "timestamp": datetime.now().isoformat()
                        })
                        logger.info(f"Found unread: {name} ({unread_count} messages)")
                    
                except Exception as e:
                    logger.debug(f"Error processing chat item: {e}")
                    continue
            
            return unread_messages
            
        except Exception as e:
            logger.error(f"Failed to get unread messages: {e}")
            return []
    
    async def get_chat_list(self) -> list[dict[str, Any]]:
        """Get list of all chats"""
        if not self.is_authenticated:
            logger.error("Not authenticated")
            return []
        
        try:
            chats = []
            
            # Take screenshot for debugging
            await self.take_screenshot("get_chats.png")
            
            # Get all chat items using the correct selector
            chat_items = await self.page.query_selector_all(
                SELECTORS["chat_list"]
            )
            
            logger.info(f"Found {len(chat_items)} chat items")
            
            for item in chat_items[:20]:  # Limit to 20 chats
                try:
                    # Get name using span[title]
                    name_element = await item.query_selector("span[title]")
                    name = await name_element.get_attribute("title") if name_element else "Unknown"
                    
                    # Skip if name is from tabs (All, Favourites, etc.)
                    if name in ["All", "Favourites", "Unread", "Groups"]:
                        continue
                    
                    # Get last message preview
                    last_msg = ""
                    try:
                        last_msg_element = await item.query_selector("div[data-testid='last-msg-status']")
                        if last_msg_element:
                            last_msg = await last_msg_element.inner_text()
                    except Exception as e:
                        logger.debug("WhatsApp last message error: %s", e)
                    
                    # Get timestamp
                    time_text = ""
                    try:
                        # Look for time in the chat item
                        time_spans = await item.query_selector_all("span")
                        for span in time_spans:
                            text = await span.inner_text()
                            if text in ["Yesterday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"] or ":" in text:
                                time_text = text
                                break
                    except Exception as e:
                        logger.debug("WhatsApp time text error: %s", e)
                    
                    # Get unread count
                    unread_count = 0
                    try:
                        unread_badge = await item.query_selector("span[data-testid='icon-unread-count']")
                        if unread_badge:
                            unread_text = await unread_badge.inner_text()
                            if unread_text.isdigit():
                                unread_count = int(unread_text)
                    except Exception as e:
                        logger.debug("WhatsApp unread count error: %s", e)
                    
                    if name and name != "Unknown":
                        chats.append({
                            "name": name,
                            "last_message": last_msg[:100] if last_msg else "",
                            "timestamp": time_text,
                            "unread_count": unread_count
                        })
                        logger.debug(f"Added chat: {name}")
                    
                except Exception as e:
                    logger.debug(f"Error processing chat item: {e}")
                    continue
            
            return chats
            
        except Exception as e:
            logger.error(f"Failed to get chat list: {e}")
            return []
    
    async def search_contact(self, query: str) -> list[dict[str, Any]]:
        """Search for a contact"""
        if not self.is_authenticated:
            return []
        
        try:
            # Click search box
            search_box = await self.page.wait_for_selector(
                SELECTORS["search_box"],
                timeout=10000
            )
            await search_box.click()
            
            # Type search query
            await self.page.keyboard.press("Control+a")
            await self.page.keyboard.type(query, delay=50)
            
            await asyncio.sleep(2)
            
            # Get search results
            results = []
            chat_items = await self.page.query_selector_all(
                "div[role='listitem']"
            )
            
            for item in chat_items[:10]:
                try:
                    name_element = await item.query_selector("span[title]")
                    name = await name_element.get_attribute("title") if name_element else "Unknown"
                    
                    # Get phone/status
                    subtitle_element = await item.query_selector("span[role='text']")
                    subtitle = await subtitle_element.inner_text() if subtitle_element else ""
                    
                    results.append({
                        "name": name,
                        "subtitle": subtitle
                    })
                    
                except Exception as e:
                    logger.debug("WhatsApp search result error: %s", e)
                    continue
            
            # Clear search
            await self.page.keyboard.press("Escape")
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search contact: {e}")
            return []
    
    async def send_typing_indicator(self, phone: str) -> bool:
        """Show typing indicator"""
        if not self.is_authenticated:
            return False
        
        try:
            phone = phone.replace("+", "").replace(" ", "").replace("-", "")
            
            # Navigate to chat
            search_box = await self.page.wait_for_selector(
                SELECTORS["search_box"],
                timeout=10000
            )
            await search_box.click()
            await self.page.keyboard.press("Control+a")
            await self.page.keyboard.type(phone, delay=50)
            await asyncio.sleep(2)
            
            # Click on chat
            try:
                chat_item = await self.page.wait_for_selector(
                    f"div[role='listitem'] span[title='{phone}']",
                    timeout=5000
                )
                await chat_item.click()
            except Exception:
                first_result = await self.page.wait_for_selector(
                    SELECTORS["chat_list"],
                    timeout=5000
                )
                await first_result.click()
            
            # Click on message box to show typing indicator
            message_box = await self.page.wait_for_selector(
                SELECTORS["message_box"],
                timeout=10000
            )
            await message_box.click()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to show typing indicator: {e}")
            return False
    
    async def take_screenshot(self, filename: str = "whatsapp_screenshot.png") -> str:
        """Take a screenshot of current state"""
        try:
            filepath = str(self.session_dir / filename)
            await self.page.screenshot(path=filepath, full_page=False)
            logger.info(f"Screenshot saved to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return ""
    
    async def stop(self):
        """Stop WhatsApp Web automation"""
        self.is_running = False
        self.is_authenticated = False
        
        try:
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.debug("WhatsApp browser close error: %s", e)
        
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.debug("WhatsApp playwright stop error: %s", e)
        
        self.browser = None
        self.playwright = None
        self.page = None
        
        logger.info("WhatsApp Web stopped")
    
    async def is_online(self) -> bool:
        """Check if WhatsApp Web is online and authenticated"""
        try:
            if not self.page or self.page.is_closed():
                return False
            
            # Check if main screen exists (indicates authenticated)
            await self.page.wait_for_selector(
                "div[data-testid='wa-web-main-screen']",
                timeout=3000
            )
            return True
            
        except Exception:
            return False


# Global instance
whatsapp_web = WhatsAppWeb(headless=False)


async def get_whatsapp_web() -> WhatsAppWeb:
    """Get WhatsApp Web instance"""
    return whatsapp_web
