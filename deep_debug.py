import asyncio
import sys
import io
sys.path.insert(0, 'D:\\cityestate')

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.services.whatsapp_web import WhatsAppWeb

async def deep_debug():
    print('=== Deep Debug ===')
    
    wa = WhatsAppWeb(headless=False)
    
    # Start
    success = await wa.start()
    print(f'Started: {success}')
    print(f'Authenticated: {wa.is_authenticated}')
    
    if not wa.is_authenticated:
        print('Waiting for authentication...')
        await asyncio.sleep(30)
    
    # Get all contenteditable elements
    print('\n=== All contenteditable elements ===')
    try:
        elements = await wa.page.query_selector_all('[contenteditable]')
        print(f'Found {len(elements)} contenteditable elements')
        for i, el in enumerate(elements):
            try:
                tag = await el.evaluate('el => el.tagName')
                classes = await el.evaluate('el => el.className')
                data_tab = await el.evaluate('el => el.getAttribute("data-tab")')
                placeholder = await el.evaluate('el => el.getAttribute("placeholder")')
                title = await el.evaluate('el => el.getAttribute("title")')
                print(f'  {i}: <{tag}> class="{classes}" data-tab="{data_tab}" placeholder="{placeholder}" title="{title}"')
            except Exception as e:
                print(f'  {i}: Error - {e}')
    except Exception as e:
        print(f'Error: {e}')
    
    # Get all div elements with role
    print('\n=== All div elements with role ===')
    try:
        elements = await wa.page.query_selector_all('div[role]')
        print(f'Found {len(elements)} div elements with role')
        for i, el in enumerate(elements[:20]):
            try:
                role = await el.evaluate('el => el.getAttribute("role")')
                classes = await el.evaluate('el => el.className')
                print(f'  {i}: role="{role}" class="{classes[:50]}"')
            except Exception as e:
                print(f'  {i}: Error - {e}')
    except Exception as e:
        print(f'Error: {e}')
    
    # Try clicking on the search area directly
    print('\n=== Trying to click search area ===')
    try:
        # Get the search box by its placeholder text
        search_box = await wa.page.evaluate('''() => {
            const elements = document.querySelectorAll('[contenteditable]');
            for (const el of elements) {
                if (el.getAttribute('placeholder') === 'Search or start a new chat' || 
                    el.textContent.includes('Search or start a new chat')) {
                    return true;
                }
            }
            return false;
        }''')
        print(f'Search box found by text: {search_box}')
    except Exception as e:
        print(f'Error: {e}')
    
    # Stop
    await wa.stop()

if __name__ == '__main__':
    asyncio.run(deep_debug())
