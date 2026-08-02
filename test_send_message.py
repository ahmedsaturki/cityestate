import asyncio
import sys
import io
sys.path.insert(0, 'D:\\cityestate')

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.services.whatsapp_web import WhatsAppWeb

async def test_send_message():
    print('=== Testing Send Message ===')
    
    wa = WhatsAppWeb(headless=False)
    
    # Start
    success = await wa.start()
    print(f'Started: {success}')
    print(f'Authenticated: {wa.is_authenticated}')
    
    if not wa.is_authenticated:
        print('Waiting for authentication...')
        await asyncio.sleep(30)
    
    # Send test message
    phone = "+201018541802"
    message = "مرحباً! هذه رسالة اختبار من CityEstate WhatsApp Web automation"
    
    print(f'\nSending message to {phone}...')
    print(f'Message: {message}')
    
    try:
        result = await wa.send_message(phone, message)
        print(f'Send result: {result}')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    
    # Take screenshot
    await wa.take_screenshot('after_send.png')
    
    # Stop
    await wa.stop()
    print('\nDone!')

if __name__ == '__main__':
    asyncio.run(test_send_message())
