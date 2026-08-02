import asyncio
import sys
import io
sys.path.insert(0, 'D:\\cityestate')

# Fix encoding for Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.services.whatsapp_web import WhatsAppWeb

async def test_whatsapp():
    print('=== Testing WhatsApp Web Service ===')
    
    # Create instance
    wa = WhatsAppWeb(headless=False)
    print('OK: WhatsAppWeb created')
    
    # Test start
    print('\n=== Starting WhatsApp Web ===')
    try:
        success = await wa.start()
        print(f'OK: Start result: {success}')
        print(f'   is_authenticated: {wa.is_authenticated}')
        print(f'   is_running: {wa.is_running}')
    except Exception as e:
        print(f'ERROR: Start failed: {e}')
        import traceback
        traceback.print_exc()
    
    # Test is_online
    print('\n=== Checking Online Status ===')
    try:
        is_online = await wa.is_online()
        print(f'OK: is_online: {is_online}')
    except Exception as e:
        print(f'ERROR: is_online check failed: {e}')
    
    # Test get_chat_list
    print('\n=== Getting Chat List ===')
    try:
        chats = await wa.get_chat_list()
        print(f'OK: Found {len(chats)} chats')
        for i, chat in enumerate(chats[:10]):
            name = chat.get('name', 'Unknown')
            last_msg = chat.get('last_message', '')[:50]
            unread = chat.get('unread_count', 0)
            unread_str = f' [{unread} unread]' if unread > 0 else ''
            print(f'  {i+1}. {name}{unread_str} - {last_msg}...')
    except Exception as e:
        print(f'ERROR: get_chat_list failed: {e}')
        import traceback
        traceback.print_exc()
    
    # Test get_unread_messages
    print('\n=== Getting Unread Messages ===')
    try:
        unread = await wa.get_unread_messages()
        print(f'OK: Found {len(unread)} unread chats')
        for msg in unread:
            name = msg.get('name', 'Unknown')
            count = msg.get('unread_count', 0)
            last_msg = msg.get('last_message', '')[:50]
            print(f'  {name}: {count} messages - {last_msg}...')
    except Exception as e:
        print(f'ERROR: get_unread_messages failed: {e}')
        import traceback
        traceback.print_exc()
    
    # Test screenshot
    print('\n=== Taking Screenshot ===')
    try:
        filepath = await wa.take_screenshot('final_test.png')
        print(f'OK: Screenshot saved: {filepath}')
    except Exception as e:
        print(f'ERROR: Screenshot failed: {e}')
    
    # Stop
    print('\n=== Stopping WhatsApp Web ===')
    try:
        await wa.stop()
        print('OK: Stopped')
    except Exception as e:
        print(f'ERROR: Stop failed: {e}')

if __name__ == '__main__':
    asyncio.run(test_whatsapp())
