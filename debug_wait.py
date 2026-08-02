import asyncio
import sys
import io
sys.path.insert(0, 'D:\\cityestate')

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.services.whatsapp_web import WhatsAppWeb

async def debug_wait_load():
    print('=== Debug Wait for Load ===')
    
    wa = WhatsAppWeb(headless=False)
    
    # Start
    success = await wa.start()
    print(f'Started: {success}')
    print(f'Authenticated: {wa.is_authenticated}')
    
    if not wa.is_authenticated:
        print('Waiting for authentication...')
        await asyncio.sleep(30)
    
    # Wait for page to fully load
    print('\n=== Waiting for page to load ===')
    await asyncio.sleep(5)
    
    # Take screenshot
    await wa.take_screenshot('debug_wait_load.png')
    
    # Try to find search box with various methods
    print('\n=== Trying to find search box ===')
    
    # Method 1: Try clicking on the search icon (magnifying glass)
    try:
        # Find the search icon by its SVG path
        search_icon = await wa.page.evaluate('''() => {
            const svgs = document.querySelectorAll('svg');
            for (const svg of svgs) {
                const paths = svg.querySelectorAll('path');
                for (const path of paths) {
                    const d = path.getAttribute('d') || '';
                    if (d.includes('M21.5') || d.includes('search')) {
                        return svg.parentElement.getAttribute('data-testid') || 'found';
                    }
                }
            }
            return null;
        }''')
        print(f'Search icon: {search_icon}')
    except Exception as e:
        print(f'Error: {e}')
    
    # Method 2: Try to find by aria-label
    try:
        elements = await wa.page.query_selector_all('[aria-label]')
        print(f'Found {len(elements)} elements with aria-label')
        for el in elements[:10]:
            label = await el.evaluate('el => el.getAttribute("aria-label")')
            print(f'  aria-label: {label}')
    except Exception as e:
        print(f'Error: {e}')
    
    # Method 3: Try to find by data-testid
    try:
        elements = await wa.page.query_selector_all('[data-testid]')
        print(f'\nFound {len(elements)} elements with data-testid')
        for el in elements[:30]:
            testid = await el.evaluate('el => el.getAttribute("data-testid")')
            print(f'  data-testid: {testid}')
    except Exception as e:
        print(f'Error: {e}')
    
    # Stop
    await wa.stop()

if __name__ == '__main__':
    asyncio.run(debug_wait_load())
