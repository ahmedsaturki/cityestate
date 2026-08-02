import asyncio
import sys
import io
sys.path.insert(0, 'D:\\cityestate')

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.services.whatsapp_web import WhatsAppWeb

async def debug_search_box():
    print('=== Debugging Search Box ===')
    
    wa = WhatsAppWeb(headless=False)
    
    # Start
    success = await wa.start()
    print(f'Started: {success}')
    print(f'Authenticated: {wa.is_authenticated}')
    
    if not wa.is_authenticated:
        print('Waiting for authentication...')
        await asyncio.sleep(30)
    
    # Take screenshot before
    await wa.take_screenshot('debug_search_before.png')
    
    # Try different search box selectors
    selectors_to_test = [
        "div[contenteditable='true'][data-tab='3']",
        "div[contenteditable='true']",
        "div[role='textbox']",
        "div[contenteditable]",
        "div[data-testid='chat-list-search']",
        "div[title='Search or start a new chat']",
        "div[aria-label='Search or start a new chat']",
        "#side div[contenteditable='true']",
        "#search div[contenteditable='true']",
    ]
    
    for selector in selectors_to_test:
        try:
            element = await wa.page.query_selector(selector)
            if element:
                print(f'SUCCESS: {selector}')
                # Try clicking it
                await element.click()
                print(f'  Clicked successfully')
                await asyncio.sleep(0.5)
            else:
                print(f'NOT FOUND: {selector}')
        except Exception as e:
            print(f'ERROR: {selector} - {e}')
    
    # Take screenshot after
    await wa.take_screenshot('debug_search_after.png')
    
    # Stop
    await wa.stop()

if __name__ == '__main__':
    asyncio.run(debug_search_box())
