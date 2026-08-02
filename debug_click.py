import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
sys.path.insert(0, 'D:\\cityestate')

from src.services.whatsapp_web import WhatsAppWeb

async def debug():
    wa = WhatsAppWeb(headless=False)
    await wa.start()
    if not wa.is_authenticated:
        await asyncio.sleep(30)
    
    # Click Ahmed from main list (NOT search)
    items = await wa.page.query_selector_all("div[data-testid='cell-frame-container']")
    for item in items:
        text = await item.inner_text()
        if "Ahmed" in text:
            await item.click()
            print(f"Clicked: {text[:40]}")
            break
    await asyncio.sleep(2)
    
    # Take screenshot of current state
    await wa.take_screenshot("debug_click1.png")
    
    # Try clicking at the bottom of the chat area where input should be
    # Use coordinates: right panel starts at ~600px, bottom of chat at ~740px
    print("Clicking at bottom of chat area...")
    await wa.page.mouse.click(900, 740)
    await asyncio.sleep(1)
    await wa.take_screenshot("debug_click2.png")
    
    # Check editables
    editables = await wa.page.evaluate('''() => {
        return document.querySelectorAll('[contenteditable]').length;
    }''')
    print(f"Editables after click: {editables}")
    
    # Try keyboard - maybe typing works even without visible input
    print("Trying keyboard type...")
    await wa.page.keyboard.type("test", delay=50)
    await asyncio.sleep(1)
    await wa.take_screenshot("debug_click3.png")
    
    # Check if restriction banner can be dismissed by clicking "Show details"
    print("Clicking Show details on restriction...")
    show_details = await wa.page.evaluate('''() => {
        const links = document.querySelectorAll('a, span, div');
        for (const el of links) {
            if (el.textContent.includes('Show details')) {
                el.click();
                return 'clicked';
            }
        }
        return 'not found';
    }''')
    print(f"Show details: {show_details}")
    await asyncio.sleep(2)
    await wa.take_screenshot("debug_click4.png")
    
    # Check editables again
    editables2 = await wa.page.evaluate('''() => {
        const els = document.querySelectorAll('[contenteditable]');
        return Array.from(els).map(el => ({
            visible: el.offsetParent !== null,
            rect: el.getBoundingClientRect()
        }));
    }''')
    print(f"Editables after show details: {len(editables2)}")
    for e in editables2:
        print(f"  visible={e['visible']} rect=({e['rect']['x']:.0f},{e['rect']['y']:.0f})")
    
    await wa.stop()

asyncio.run(debug())
