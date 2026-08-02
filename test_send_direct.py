import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, 'D:\\cityestate')

from src.services.whatsapp_web import WhatsAppWeb

async def test():
    wa = WhatsAppWeb(headless=False)
    await wa.start()
    print(f"Auth: {wa.is_authenticated}")
    if not wa.is_authenticated:
        await asyncio.sleep(30)
    
    # Search
    container = await wa.page.wait_for_selector("div[data-testid='chat-list-search-container']", timeout=10000)
    await container.click()
    await asyncio.sleep(1)
    await wa.page.keyboard.type("+201018541802", delay=50)
    await asyncio.sleep(3)
    
    # Screenshot after search
    await wa.take_screenshot("debug_send_1.png")
    
    # Find all clickable items
    items = await wa.page.query_selector_all("[data-testid='cell-frame-container']")
    print(f"Found {len(items)} cell-frame items")
    
    if items:
        await items[0].click()
        print("Clicked first item")
        await asyncio.sleep(2)
        
        # Screenshot after click
        await wa.take_screenshot("debug_send_2.png")
        
        # Now check what's on page
        footer = await wa.page.query_selector("footer")
        print(f"Footer found: {footer is not None}")
        
        editables = await wa.page.query_selector_all("footer [contenteditable='true']")
        print(f"Footer editables: {len(editables)}")
        
        all_editables = await wa.page.query_selector_all("[contenteditable='true']")
        print(f"All editables: {len(all_editables)}")
        for i, el in enumerate(all_editables):
            tag = await el.evaluate('el => el.tagName')
            vis = await el.is_visible()
            print(f"  {i}: <{tag}> visible={vis}")
        
        # Type message
        if editables:
            await editables[0].click()
            await asyncio.sleep(0.3)
            await wa.page.keyboard.type("Test from API", delay=30)
            await asyncio.sleep(0.5)
            await wa.take_screenshot("debug_send_3.png")
            
            # Send
            send = await wa.page.query_selector("span[data-icon='send']")
            print(f"Send button: {send is not None}")
            if send:
                await send.click()
                print("SENT!")
            else:
                await wa.page.keyboard.press("Enter")
                print("SENT via Enter!")
            
            await asyncio.sleep(2)
            await wa.take_screenshot("debug_send_4.png")
    
    await wa.stop()

asyncio.run(test())
