import asyncio
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, 'D:\\cityestate')

from src.services.whatsapp_web import WhatsAppWeb

async def test_send():
    wa = WhatsAppWeb(headless=False)
    await wa.start()
    print(f"Authenticated: {wa.is_authenticated}")
    if not wa.is_authenticated:
        print("Waiting for auth...")
        await asyncio.sleep(30)

    # --- Step 1: Find the actual search input ---
    print("\n=== Step 1: Find search input ===")
    
    # Try clicking the container first, then look for input
    container = await wa.page.query_selector("div[data-testid='chat-list-search-container']")
    print(f"Container found: {container is not None}")
    
    if container:
        # Click on the container to activate the search
        await container.click()
        await asyncio.sleep(1)
        
        # Now look for contenteditable that appeared
        editables = await wa.page.query_selector_all('[contenteditable="true"]')
        print(f"Contenteditable elements after click: {len(editables)}")
        for i, el in enumerate(editables):
            tag = await el.evaluate('el => el.tagName')
            ph = await el.evaluate('el => el.getAttribute("placeholder")')
            dt = await el.evaluate('el => el.getAttribute("data-tab")')
            vis = await el.is_visible()
            print(f"  {i}: <{tag}> placeholder={ph} data-tab={dt} visible={vis}")
    
    # --- Step 2: Try typing in search ---
    print("\n=== Step 2: Try search ===")
    
    phone = "+201018541802"
    
    # Method: Use page.click with position on the search area
    try:
        await wa.page.click("div[data-testid='chat-list-search-container']", timeout=5000)
        await asyncio.sleep(1)
        
        # Check if input appeared
        editables = await wa.page.query_selector_all('[contenteditable="true"]')
        print(f"Contenteditable after click: {len(editables)}")
        
        if editables:
            for el in editables:
                vis = await el.is_visible()
                if vis:
                    await el.click()
                    await asyncio.sleep(0.3)
                    await wa.page.keyboard.type(phone, delay=50)
                    print(f"Typed: {phone}")
                    break
        else:
            # Fallback: use keyboard shortcut or click directly
            print("No contenteditable found, trying keyboard...")
            await wa.page.keyboard.type(phone, delay=50)
        
        await asyncio.sleep(3)
        await wa.take_screenshot("test_send_search.png")
        
        # Look for results
        results = await wa.page.query_selector_all("[data-testid='cell-frame-container']")
        print(f"Chat results: {len(results)}")
        
        if results:
            # Click first result
            await results[0].click()
            await asyncio.sleep(2)
            await wa.take_screenshot("test_send_chat.png")
            
            # Type message
            msg_box = await wa.page.query_selector("footer div[contenteditable='true']")
            if msg_box:
                await msg_box.click()
                await asyncio.sleep(0.3)
                await wa.page.keyboard.type("مرحبا! رسالة اختبار من CityEstate", delay=30)
                await asyncio.sleep(0.5)
                await wa.take_screenshot("test_send_typed.png")
                
                # Send
                send_btn = await wa.page.query_selector("span[data-icon='send']")
                if send_btn:
                    await send_btn.click()
                    await asyncio.sleep(2)
                    await wa.take_screenshot("test_send_sent.png")
                    print("Message SENT!")
                else:
                    print("Send button not found, trying Enter")
                    await wa.page.keyboard.press("Enter")
                    await asyncio.sleep(2)
                    await wa.take_screenshot("test_send_sent.png")
                    print("Message SENT via Enter!")
            else:
                print("Message box not found")
        else:
            print("No search results")
    except Exception as e:
        print(f"Error: {e}")
        await wa.take_screenshot("test_send_error.png")
    
    await wa.stop()
    print("\nDone!")

asyncio.run(test_send())
