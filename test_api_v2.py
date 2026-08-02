import httpx, time
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

    # 3. Wait and check status
    time.sleep(5)
    print("\n[3] GET /status (after start)")
    r = c.get("/status")
    print(f"    {r.status_code}: {r.json()}")

    # 4. Get chats
    print("\n[4] GET /chats")
    r = c.get("/chats")
    print(f"    {r.status_code}: {r.json()}")

    # 5. Get unread
    print("\n[5] GET /unread")
    r = c.get("/unread")
    data = r.json()
    print(f"    {r.status_code}: count={data.get('count', 0)}")

    # 6. Search
    print("\n[6] GET /search?query=Aahmed")
    r = c.get("/search", params={"query": "Aahmed"})
    print(f"    {r.status_code}: {r.json()}")

    # 7. Screenshot
    print("\n[7] GET /screenshot")
    r = c.get("/screenshot")
    print(f"    {r.status_code}: {r.json()}")

    # 8. Send message
    print("\n[8] POST /send")
    r = c.post("/send", json={
        "to": "+201018541802",
        "message": "CityEstate API test!"
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
    print(f"    {r.status_code}: {r.json()}")

print("\n" + "=" * 60)
print("  All endpoints tested!")
print("=" * 60)
