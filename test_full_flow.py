import httpx, time
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE = "http://localhost:8000/api/v1/webhooks/whatsapp-web"

print("=" * 60)
print("  WhatsApp Web API - Full Flow Test")
print("=" * 60)

with httpx.Client(base_url=BASE, timeout=120) as c:

    # 1. Status (not started)
    print("\n[1] GET /status (before start)")
    r = c.get("/status")
    print(f"    {r.json()}")

    # 2. Start (non-blocking, should return quickly)
    print("\n[2] POST /start (non-blocking)")
    r = c.post("/start")
    print(f"    {r.status_code}: {r.json()}")

    # 3. Poll status until authenticated (QR scan or session restore)
    print("\n[3] Polling /status for auth...")
    for i in range(30):
        time.sleep(2)
        r = c.get("/status")
        data = r.json()
        print(f"    Poll {i+1}: authenticated={data['is_authenticated']}")
        if data["is_authenticated"]:
            break

    if not data["is_authenticated"]:
        print("\n    ⚠️  Not authenticated after 60s. Check browser window.")
        print("    Scan QR code if needed, then re-run test.")
    else:
        print("\n    ✓ Authenticated!")

        # 4. Get chats
        print("\n[4] GET /chats")
        r = c.get("/chats")
        data = r.json()
        print(f"    {data['count']} chats")
        for ch in data.get("chats", [])[:5]:
            print(f"      - {ch.get('name', 'N/A')}")

        # 5. Get unread
        print("\n[5] GET /unread")
        r = c.get("/unread")
        data = r.json()
        print(f"    {data['count']} unread messages")
        for msg in data.get("messages", [])[:3]:
            print(f"      - {msg.get('chat_name')}: {str(msg.get('text', ''))[:50]}")

        # 6. Search
        print("\n[6] GET /search?query=Ahmed")
        r = c.get("/search", params={"query": "Ahmed"})
        print(f"    {r.status_code}: {r.json()}")

        # 7. Screenshot
        print("\n[7] GET /screenshot")
        r = c.get("/screenshot")
        data = r.json()
        print(f"    {r.status_code}: file={data.get('file')}")

        # 8. Send message
        print("\n[8] POST /send")
        r = c.post("/send", json={
            "to": "+201018541802",
            "message": "CityEstate API test - تم الارسال بنجاح!"
        })
        print(f"    {r.status_code}: {r.json()}")

    # 9. Stop
    print("\n[9] POST /stop")
    r = c.post("/stop")
    print(f"    {r.status_code}: {r.json()}")

    # 10. Final status
    time.sleep(2)
    print("\n[10] GET /status (final)")
    r = c.get("/status")
    print(f"    {r.json()}")

print("\n" + "=" * 60)
print("  Done!")
print("=" * 60)
