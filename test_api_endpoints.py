import httpx
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE = "http://localhost:8000/api/v1/webhooks/whatsapp-web"

print("=" * 60)
print("  Testing WhatsApp Web API Endpoints")
print("=" * 60)

with httpx.Client(base_url=BASE, timeout=30) as c:

    # 1. Status
    print("\n[1] GET /status")
    r = c.get("/status")
    print(f"    {r.status_code}: {r.json()}")

    # 2. Start
    print("\n[2] POST /start")
    r = c.post("/start")
    print(f"    {r.status_code}: {r.json()}")

    # 3. Status after start
    import time; time.sleep(3)
    print("\n[3] GET /status (after start)")
    r = c.get("/status")
    print(f"    {r.status_code}: {r.json()}")

    # 4. Get chats
    print("\n[4] GET /chats")
    r = c.get("/chats")
    data = r.json()
    print(f"    {r.status_code}: {len(data.get('chats', []))} chats")
    if data.get('chats'):
        for ch in data['chats'][:3]:
            print(f"      - {ch.get('name', 'N/A')}")

    # 5. Get unread
    print("\n[5] GET /unread")
    r = c.get("/unread")
    data = r.json()
    print(f"    {r.status_code}: {len(data.get('messages', []))} unread messages")
    for msg in data.get('messages', [])[:3]:
        print(f"      - {msg.get('chat_name')}: {msg.get('text', '')[:40]}")

    # 6. Search
    print("\n[6] GET /search?q=Aahmed")
    r = c.get("/search", params={"q": "Aahmed"})
    print(f"    {r.status_code}: {r.json()}")

    # 7. Screenshot
    print("\n[7] GET /screenshot")
    r = c.get("/screenshot")
    data = r.json()
    print(f"    {r.status_code}: file={data.get('file')}")

    # 8. Send message
    print("\n[8] POST /send")
    r = c.post("/send", json={
        "phone": "+201018541802",
        "message": "CityEstate API test - تم الارسال بنجاح!"
    })
    print(f"    {r.status_code}: {r.json()}")

    # 9. Stop
    print("\n[9] POST /stop")
    r = c.post("/stop")
    print(f"    {r.status_code}: {r.json()}")

    # 10. Final status
    print("\n[10] GET /status (final)")
    r = c.get("/status")
    print(f"    {r.status_code}: {r.json()}")

print("\n" + "=" * 60)
print("  All endpoints tested!")
print("=" * 60)
