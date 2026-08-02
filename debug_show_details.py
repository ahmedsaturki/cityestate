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
    
    # Click Ahmed from main list
    items = await wa.page.query_selector_all("div[data-testid='cell-frame-container']")
    for item in items:
        text = await item.inner_text()
        if "Ahmed" in text:
            await item.click()
            print(f"Clicked: {text[:40]}")
            break
    await asyncio.sleep(2)
    
    # Close "Calling on web" popup via JS
    await wa.page.evaluate('''() => {
        document.querySelectorAll('span[data-icon="x"]').forEach(el => {
            const btn = el.closest('[role="button"]') || el.parentElement;
            if (btn && btn.offsetParent !== null) btn.click();
        });
    }''')
    await asyncio.sleep(1)
    print("Popup dismissed")
    
    # Click "Show details" on restriction banner
    clicked = await wa.page.evaluate('''() => {
        const all = document.querySelectorAll('*');
        for (const el of all) {
            if (el.textContent === 'Show details' && el.offsetParent !== null) {
                el.click();
                return true;
            }
        }
        return false;
    }''')
    print(f"Clicked Show details: {clicked}")
    await asyncio.sleep(3)
    
    await wa.take_screenshot("debug_show_details.png")
    
    # Check for editables
    editables = await wa.page.evaluate('''() => {
        return Array.from(document.querySelectorAll('[contenteditable]')).map(el => ({
            visible: el.offsetParent !== null,
            rect: el.getBoundingClientRect(),
            tag: el.tagName
        }));
    }''')
    print(f"Editables: {len(editables)}")
    for e in editables:
        print(f"  <{e['tag']}> visible={e['visible']} rect=({e['rect']['x']:.0f},{e['rect']['y']:.0f}) {e['rect']['width']:.0f}x{e['rect']['height']:.0f}")
    
    # Check for footer
    footer = await wa.page.evaluate('''() => {
        const f = document.querySelector('footer');
        if (!f) return null;
        return {
            visible: f.offsetParent !== null,
            rect: f.getBoundingClientRect(),
            childCount: f.children.length,
            html: f.innerHTML.substring(0, 300)
        };
    }''')
    print(f"Footer: {footer}")
    
    # Try clicking the area where input should be
    print("Clicking at (900, 750)...")
    await wa.page.mouse.click(900, 750)
    await asyncio.sleep(1)
    
    editables2 = await wa.page.evaluate('''() => {
        return document.querySelectorAll('[contenteditable]').length;
    }''')
    print(f"Editables after click: {editables2}")
    await wa.take_screenshot("debug_after_click.png")
    
    await wa.stop()

asyncio.run(debug())
