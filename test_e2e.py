"""
Comprehensive end-to-end test for all endpoints with Authentication.
Run with:  python test_e2e.py
"""
import json
import sys
import urllib.request
import urllib.error
import time

BASE = "http://localhost:8000"
PASS, FAIL = 0, 0
TOKEN = None


def req(method, path, body=None, auth=False):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    if auth and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
        
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else None
    except Exception as e:
        return 0, {"error": str(e)}


def check(label, status, data, expected_status):
    global PASS, FAIL
    ok = status == expected_status
    icon = "✅" if ok else "❌"
    print(f"{icon} [{status}] {label}")
    if not ok:
        print(f"   Expected {expected_status}, got {status}")
        print(f"   Response: {json.dumps(data, indent=2)[:300]}")
        FAIL += 1
    else:
        PASS += 1
    return data


print("\n" + "=" * 55)
print("  PackageGo API — Full E2E Test (with Auth)")
print("=" * 55)

# Wait for server if starting
try:
    req("GET", "/")
except:
    print("Waiting for server...")
    time.sleep(2)

# 1. Auth & Registry
print("\n── Auth ──")
# Register a unique user for this test run
unique_suffix = int(time.time())
username = f"testuser_{unique_suffix}"
email = f"{username}@example.com"

s, d = req("POST", "/auth/register", {
    "username": username, "email": email, "password": "password123",
    "first_name": "E2E", "last_name": "Tester"
})
check("POST /auth/register", s, d, 201)

s, d = req("POST", "/auth/login", {
    "username": username, "password": "password123"
})
login_data = check("POST /auth/login", s, d, 200)
if login_data and "access_token" in login_data:
    TOKEN = login_data["access_token"]
else:
    print("Failed to get token, aborting tests.")
    sys.exit(1)

s, d = req("GET", "/auth/me", auth=True)
me = check("GET /auth/me", s, d, 200)

# 2. Travelers
print("\n── Travelers ──")
s, d = req("POST", "/travelers", {
    "name": "E2E Traveler", "email": email,
    "phone": "+1-555-0001", "bio": "E2E bio"
}, auth=True)
t = check("POST /travelers", s, d, 201)
tid = t["id"] if t else 0

s, d = req("GET", "/travelers")
check("GET /travelers (public)", s, d, 200)

s, d = req("PUT", f"/travelers/{tid}", {
    "name": "E2E Traveler Upd", "email": email,
    "phone": "+1-555-0002", "bio": "Updated bio"
}, auth=True)
check(f"PUT /travelers/{tid}", s, d, 200)

# 3. Senders
print("\n── Senders ──")
s, d = req("POST", "/senders", {
    "name": "E2E Sender", "email": email,
    "phone": "+1-555-0003", "city": "NYC"
}, auth=True)
snd = check("POST /senders", s, d, 201)
sid = snd["id"] if snd else 0

# 4. Trips
print("\n── Trips ──")
s, d = req("POST", "/trips", {
    "traveler_id": tid, "from_city": "NYC", "to_city": "LA",
    "departure_date": "2026-12-01", "arrival_date": "2026-12-05",
    "available_weight_kg": 20.0, "status": "open"
}, auth=True)
trp = check("POST /trips", s, d, 201)
trid = trp["id"] if trp else 0

# 5. Packages
print("\n── Packages ──")
s, d = req("POST", "/packages", {
    "sender_id": sid, "description": "Important Box",
    "pickup_city": "NYC", "delivery_city": "LA",
    "weight_kg": 5.0, "size": "medium", "reward": 100.0,
    "deadline": "2026-12-10", "status": "pending"
}, auth=True)
pkg = check("POST /packages", s, d, 201)
pid = pkg["id"] if pkg else 0

# 6. Accept Package & Status Flow
print("\n── Package Flow ──")
s, d = req("POST", f"/packages/{pid}/accept", {"traveler_id": tid}, auth=True)
check("POST /packages/{id}/accept", s, d, 200)

s, d = req("PATCH", f"/packages/{pid}/status", {"status": "in_transit"}, auth=True)
check("PATCH /packages/{id}/status (in_transit)", s, d, 200)

s, d = req("PATCH", f"/packages/{pid}/status", {"status": "delivered"}, auth=True)
check("PATCH /packages/{id}/status (delivered)", s, d, 200)

# 7. Reviews
print("\n── Reviews ──")
s, d = req("POST", "/reviews", {
    "sender_id": sid, "traveler_id": tid, "package_id": pid,
    "rating": 5, "comment": "Excellent!"
}, auth=True)
rev = check("POST /reviews", s, d, 201)
rid = rev["id"] if rev else 0

# 8. Notifications
print("\n── Notifications ──")
# We registered as a regular user, so we shouldn't be able to CREATE notifications (admin only)
s, d = req("POST", "/notifications", {
    "user_id": me["id"], "title": "Test", "message": "Msg", "notification_type": "info"
}, auth=True)
check("POST /notifications (user should fail)", s, d, 403)

s, d = req("GET", "/notifications", auth=True)
check("GET /notifications", s, d, 200)

# 9. Cleanup
print("\n── Cleanup ──")
# Only admins can delete anything now, except owners can delete their own. Let's delete them.
s, d = req("DELETE", f"/reviews/{rid}", auth=True)
check("DELETE /reviews", s, d, 204)

# Can't delete delivered package.
# Oh, we changed status to delivered. The cleanup might fail if it's terminal.
# Let's try to delete a delivered package, should fail? The edge cases didn't prevent delete of delivered? Wait, "if package.status == 'in_transit': raise...". Delivered can be deleted.
s, d = req("DELETE", f"/packages/{pid}", auth=True)
check("DELETE /packages", s, d, 204)

s, d = req("DELETE", f"/trips/{trid}", auth=True)
check("DELETE /trips", s, d, 204)

s, d = req("DELETE", f"/senders/{sid}", auth=True)
check("DELETE /senders", s, d, 204)

s, d = req("DELETE", f"/travelers/{tid}", auth=True)
check("DELETE /travelers", s, d, 204)


# 10. Summary
print("\n" + "=" * 55)
print(f"  Results: {PASS} passed  |  {FAIL} failed")
print("=" * 55 + "\n")

sys.exit(0 if FAIL == 0 else 1)
