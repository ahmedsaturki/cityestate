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
    
    # Dismiss popups first
    print("Dismissing popups...")
    await wa._dismiss_popups()
    await asyncio.sleep(1)
    await wa.take_screenshot("test_v3_1.png")
    
    # Try send
    print("Sending message...")
    result = await wa.send_message("+201018541802", "CityEstate v3 test!")
    print(f"Result: {result}")
    
    await wa.stop()

asyncio.run(test())
