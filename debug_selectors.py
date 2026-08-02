import asyncio
import sys
sys.path.insert(0, 'D:\\cityestate')

from src.services.whatsapp_web import WhatsAppWeb

async def debug_selectors():
    print('=== Debugging WhatsApp Web Selectors ===')
    
    wa = WhatsAppWeb(headless=False)
    
    # Start
    success = await wa.start()
    print(f'Started: {success}')
    print(f'Authenticated: {wa.is_authenticated}')
    
    if not wa.is_authenticated:
        print('Not authenticated, waiting for QR scan...')
        await asyncio.sleep(30)
    
    # Take screenshot
    await wa.take_screenshot('debug_before.png')
    
    # Try different selectors
    selectors_to_test = [
        "div[role='listitem']",
        "div[data-testid='cell-frame-container']",
        "div[data-testid='chat-list'] div[role='listitem']",
        "#pane-side div[role='listitem']",
        "div[role='list'] div[role='listitem']",
        "div[class*='chat']",
        "div[class*='list']",
        "span[title]",
    ]
    
    for selector in selectors_to_test:
        try:
            elements = await wa.page.query_selector_all(selector)
            print(f'Selector: {selector}')
            print(f'  Found: {len(elements)} elements')
            if elements:
                for i, el in enumerate(elements[:3]):
                    text = await el.inner_text()
                    print(f'    {i}: {text[:50]}...' if len(text) > 50 else f'    {i}: {text}')
        except Exception as e:
            print(f'Selector: {selector}')
            print(f'  Error: {e}')
        print()
    
    # Get page content structure
    print('\n=== Page Structure ===')
    try:
        # Get the main content area
        main_content = await wa.page.query_selector("div[data-testid='default-user']")
        if main_content:
            print('Found main content area')
        
        # Get the chat panel
        chat_panel = await wa.page.query_selector("div[data-testid='chat-list']")
        if chat_panel:
            print('Found chat panel')
            children = await chat_panel.query_selector_all("*")
            print(f'  Children count: {len(children)}')
    except Exception as e:
        print(f'Error: {e}')
    
    # Stop
    await wa.stop()

if __name__ == '__main__':
    asyncio.run(debug_selectors())
