import asyncio
import sys
import io
sys.path.insert(0, 'D:\\cityestate')

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.services.whatsapp_web import WhatsAppWeb

async def debug_new_chat():
    print('=== Debug New Chat Button ===')
    
    wa = WhatsAppWeb(headless=False)
    
    # Start
    success = await wa.start()
    print(f'Started: {success}')
    print(f'Authenticated: {wa.is_authenticated}')
    
    if not wa.is_authenticated:
        print('Waiting for authentication...')
        await asyncio.sleep(30)
    
    # Take screenshot
    await wa.take_screenshot('debug_new_chat.png')
    
    # Try different selectors for new chat button
    selectors_to_test = [
        "div[data-testid='icon-search']",
        "div[data-testid='search-icon']",
        "span[data-icon='search']",
        "div[title='New chat']",
        "div[data-testid='new-chat-button']",
        "div[data-testid='icon-chat']",
        "span[data-icon='chat']",
    ]
    
    for selector in selectors_to_test:
        try:
            element = await wa.page.query_selector(selector)
            if element:
                print(f'FOUND: {selector}')
            else:
                print(f'NOT FOUND: {selector}')
        except Exception as e:
            print(f'ERROR: {selector} - {e}')
    
    # Try to find by text content
    print('\n=== Searching by text ===')
    try:
        result = await wa.page.evaluate('''() => {
            const elements = document.querySelectorAll('*');
            const found = [];
            for (const el of elements) {
                const text = el.textContent || el.getAttribute('title') || '';
                if (text.includes('Search') || text.includes('New chat')) {
                    found.push({
                        tag: el.tagName,
                        text: text.substring(0, 50),
                        class: el.className.substring(0, 50),
                        testid: el.getAttribute('data-testid')
                    });
                }
            }
            return found.slice(0, 10);
        }''')
        print(f'Elements with Search/New chat text: {result}')
    except Exception as e:
        print(f'Error: {e}')
    
    # Stop
    await wa.stop()

if __name__ == '__main__':
    asyncio.run(debug_new_chat())
