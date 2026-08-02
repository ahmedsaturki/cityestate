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
    
    # 1. Find all elements with data-icon
    icons = await wa.page.evaluate('''() => {
        const els = document.querySelectorAll('[data-icon]');
        return Array.from(els).map(el => ({
            icon: el.getAttribute('data-icon'),
            visible: el.offsetParent !== null,
            tag: el.tagName,
            rect: el.getBoundingClientRect()
        })).filter(e => e.visible);
    }''')
    print("Visible icons:")
    for icon in icons:
        print(f"  {icon['icon']} <{icon['tag']}> at ({icon['rect']['x']:.0f},{icon['rect']['y']:.0f})")
    
    # 2. Find all contenteditable elements
    editables = await wa.page.evaluate('''() => {
        const els = document.querySelectorAll('[contenteditable]');
        return Array.from(els).map(el => ({
            tag: el.tagName,
            editable: el.contentEditable,
            visible: el.offsetParent !== null,
            rect: el.getBoundingClientRect(),
            id: el.id,
            classes: el.className.substring(0, 60)
        }));
    }''')
    print(f"\nAll contenteditable ({len(editables)}):")
    for e in editables:
        print(f"  <{e['tag']}> editable={e['editable']} visible={e['visible']} id={e['id']} class={e['classes']}")
        print(f"    rect: ({e['rect']['x']:.0f},{e['rect']['y']:.0f}) {e['rect']['width']:.0f}x{e['rect']['height']:.0f}")
    
    # 3. Find footer element
    footer = await wa.page.evaluate('''() => {
        const f = document.querySelector('footer');
        if (!f) return null;
        return {
            tag: f.tagName,
            html: f.innerHTML.substring(0, 200),
            childCount: f.children.length,
            rect: f.getBoundingClientRect()
        };
    }''')
    print(f"\nFooter: {footer}")
    
    # 4. Find the restriction banner
    banner = await wa.page.evaluate('''() => {
        const el = document.querySelector('[data-testid="chat-butterbar"]');
        if (!el) return null;
        return {
            text: el.textContent,
            visible: el.offsetParent !== null,
            rect: el.getBoundingClientRect()
        };
    }''')
    print(f"\nRestriction banner: {banner}")
    
    # 5. Click the X on "Calling on web" popup
    print("\nClicking popup X...")
    await wa.page.evaluate('''() => {
        // Find the X in the popup
        const svgs = document.querySelectorAll('svg[data-icon="x"]');
        console.log('Found x svgs:', svgs.length);
        svgs.forEach(svg => {
            const parent = svg.closest('[role="button"]') || svg.parentElement;
            if (parent) parent.click();
        });
        
        // Also try span[data-icon="x"]
        const spans = document.querySelectorAll('span[data-icon="x"]');
        console.log('Found x spans:', spans.length);
        spans.forEach(span => {
            const parent = span.closest('[role="button"]') || span.parentElement;
            if (parent) parent.click();
        });
    }''')
    await asyncio.sleep(1)
    await wa.take_screenshot("debug_after_dismiss.png")
    
    # 6. Clear search and click from list
    print("\nClearing search...")
    await wa.page.evaluate('''() => {
        const x = document.querySelector('span[data-icon="x"]');
        if (x) {
            const btn = x.closest('[role="button"]') || x.parentElement;
            if (btn) btn.click();
        }
    }''')
    await asyncio.sleep(1)
    
    # Click chat from list
    print("Clicking chat from list...")
    items = await wa.page.query_selector_all("div[data-testid='cell-frame-container']")
    for item in items:
        text = await item.inner_text()
        if "Ahmed" in text or "201018541802" in text:
            await item.click()
            print(f"Clicked: {text[:30]}")
            break
    await asyncio.sleep(2)
    await wa.take_screenshot("debug_chat_clicked.png")
    
    # 7. Check editables again
    editables2 = await wa.page.evaluate('''() => {
        const els = document.querySelectorAll('[contenteditable]');
        return Array.from(els).map(el => ({
            tag: el.tagName,
            editable: el.contentEditable,
            visible: el.offsetParent !== null,
            rect: el.getBoundingClientRect()
        }));
    }''')
    print(f"\nEditables after click ({len(editables2)}):")
    for e in editables2:
        print(f"  <{e['tag']}> editable={e['editable']} visible={e['visible']} rect=({e['rect']['x']:.0f},{e['rect']['y']:.0f}) {e['rect']['width']:.0f}x{e['rect']['height']:.0f}")
    
    await wa.stop()

asyncio.run(debug())
