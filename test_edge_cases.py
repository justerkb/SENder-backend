"""
Comprehensive test for API edge cases and validations.
Run with: python test_edge_cases.py
Requires the server to be running on localhost:8000
"""
import json
import sys
import urllib.request
import urllib.error
import time

BASE = "http://localhost:8000"
PASS, FAIL = 0, 0
TOKEN1, TOKEN2 = None, None
ME1, ME2 = None, None

def req(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
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

def check_fail(label, status, data, expected_statuses):
    global PASS, FAIL
    if isinstance(expected_statuses, int):
        expected_statuses = [expected_statuses]
        
    ok = status in expected_statuses
    icon = "✅" if ok else "❌"
    print(f"{icon} [{status}] {label} -> {data.get('detail', data) if data else ''}")
    if not ok:
        print(f"   Expected one of {expected_statuses}, got {status}")
        FAIL += 1
    else:
        PASS += 1
    return data

def setup_users():
    global TOKEN1, TOKEN2, ME1, ME2
    u1 = f"user1_{int(time.time())}"
    u2 = f"user2_{int(time.time())}"
    
    # User 1 (Sender)
    st, reg1 = req("POST", "/auth/register", {"username": u1, "email": f"{u1}@x.com", "password": "password123", "first_name": "U1", "last_name": "L1"})
    print("Reg1:", st, reg1)
    st, login1 = req("POST", "/auth/login", {"username": u1, "password": "password123"})
    print("Login1:", st, login1)
    TOKEN1 = login1["access_token"]
    _, ME1 = req("GET", "/auth/me", token=TOKEN1)
    
    # User 2 (Traveler)
    st, reg2 = req("POST", "/auth/register", {"username": u2, "email": f"{u2}@x.com", "password": "password123", "first_name": "U2", "last_name": "L2"})
    print("Reg2:", st, reg2)
    st, login2 = req("POST", "/auth/login", {"username": u2, "password": "password123"})
    print("Login2:", st, login2)
    TOKEN2 = login2["access_token"]
    _, ME2 = req("GET", "/auth/me", token=TOKEN2)

print("\n" + "=" * 55)
print("  PackageGo API — Edge Case Tests")
print("=" * 55)

try:
    req("GET", "/")
except:
    print("Waiting for server...")
    time.sleep(2)

setup_users()

# ─── 1. SENDER & TRAVELER PROFILES ───
print("\n── Profile Edge Cases ──")
st, s1 = req("POST", "/senders", {"name": "Sender 1", "email": f"s_{int(time.time())}@x.com", "phone": "+1-555-0011", "city": "NY"}, token=TOKEN1)
if st != 201:
    print("FAILED TO CREATE SENDER", s1)
    sys.exit(1)
sid1 = s1["id"]

s, d = req("POST", "/senders", {"name": "Sender Duplicate", "email": f"s_{int(time.time())}_2@x.com", "phone": "+1-555-0012", "city": "LA"}, token=TOKEN1)
check_fail("One sender profile per user", s, d, [409, 400])

st, t2 = req("POST", "/travelers", {"name": "Traveler 2", "email": f"t_{int(time.time())}@x.com", "phone": "+1-555-0013", "bio": "Hi"}, token=TOKEN2)
if st != 201:
    print("FAILED TO CREATE TRAVELER", t2)
    sys.exit(1)
tid2 = t2["id"]

s, d = req("POST", "/travelers", {"name": "Traveler Duplicate", "email": f"t_{int(time.time())}_2@x.com", "phone": "+1-555-0014", "bio": "Hi"}, token=TOKEN2)
check_fail("One traveler profile per user", s, d, [409, 400])

# ─── 2. TRIPS ───
print("\n── Trip Edge Cases ──")
s, d = req("POST", "/trips", {
    "traveler_id": tid2, "from_city": "NY", "to_city": "NY", 
    "departure_date": "2026-10-01", "arrival_date": "2026-10-05", "available_weight_kg": 10
}, token=TOKEN2)
check_fail("Same origin and destination city", s, d, 400)

s, d = req("POST", "/trips", {
    "traveler_id": tid2, "from_city": "NY", "to_city": "LA", 
    "departure_date": "2026-10-05", "arrival_date": "2026-10-01", "available_weight_kg": 10
}, token=TOKEN2)
check_fail("Arrival before departure", s, d, 400)

s, d = req("POST", "/trips", {
    "traveler_id": tid2, "from_city": "NY", "to_city": "LA", 
    "departure_date": "2020-10-01", "arrival_date": "2020-10-05", "available_weight_kg": 10
}, token=TOKEN2)
check_fail("Departure date in the past", s, d, 400)

# Valid trip
_, trip_valid = req("POST", "/trips", {
    "traveler_id": tid2, "from_city": "NY", "to_city": "LA", 
    "departure_date": "2026-12-01", "arrival_date": "2026-12-10", "available_weight_kg": 10
}, token=TOKEN2)
trid_valid = trip_valid["id"]

s, d = req("POST", "/trips", {
    "traveler_id": tid2, "from_city": "BOS", "to_city": "CHI", 
    "departure_date": "2026-12-05", "arrival_date": "2026-12-15", "available_weight_kg": 10
}, token=TOKEN2)
check_fail("Trip date overlap for same traveler", s, d, 409)

# ─── 3. PACKAGES ───
print("\n── Package Edge Cases ──")
s, d = req("POST", "/packages", {
    "sender_id": sid1, "description": "Box", "pickup_city": "NY", "delivery_city": "NY",
    "weight_kg": 5, "size": "medium", "reward": 50, "deadline": "2026-12-20", "status": "pending"
}, token=TOKEN1)
check_fail("Same pickup and delivery city", s, d, 400)

s, d = req("POST", "/packages", {
    "sender_id": sid1, "description": "Box", "pickup_city": "NY", "delivery_city": "LA",
    "weight_kg": 5, "size": "medium", "reward": 50, "deadline": "2026-12-20", "status": "accepted"
}, token=TOKEN1)
check_fail("New package must be 'pending'", s, d, 400)

# Valid Package
_, pkg = req("POST", "/packages", {
    "sender_id": sid1, "description": "Box", "pickup_city": "NY", "delivery_city": "LA",
    "weight_kg": 15, "size": "large", "reward": 50, "deadline": "2026-12-20", "status": "pending"
}, token=TOKEN1)
pid = pkg["id"]

s, d = req("POST", f"/packages/{pid}/accept", {"traveler_id": tid2}, token=TOKEN2)
check_fail("Accept package when traveler trip exists but not enough weight (15kg pkg vs 10kg capacity)", s, d, 400)

# Fix package weight so it can be accepted
req("PATCH", f"/packages/{pid}", {"weight_kg": 5}, token=TOKEN1)
s, d = req("POST", f"/packages/{pid}/accept", {"traveler_id": tid2}, token=TOKEN2)
if s == 200:
    print(f"✅ [200] Accept package within weight limits (Valid step)")
else:
    print(f"❌ Failed to accept valid package: {d}")

s, d = req("POST", f"/packages/{pid}/accept", {"traveler_id": tid2}, token=TOKEN2)
check_fail("Accepting already accepted package", s, d, 400)

s, d = req("PATCH", f"/packages/{pid}/status", {"status": "delivered"}, token=TOKEN1)
check_fail("Invalid status transition (accepted -> delivered directly)", s, d, 400)

# ─── 4. REVIEWS ───
print("\n── Review Edge Cases ──")
s, d = req("POST", "/reviews", {
    "sender_id": sid1, "traveler_id": tid2, "package_id": pid, "rating": 5, "comment": "Nice"
}, token=TOKEN1)
check_fail("Reviewing package that is not 'delivered'", s, d, 400)

s, d = req("DELETE", f"/trips/{trid_valid}", token=TOKEN2)
check_fail("Deleting trip with active package on route", s, d, 400)

# Complete the delivery
req("PATCH", f"/packages/{pid}/status", {"status": "in_transit"}, token=TOKEN1)
req("PATCH", f"/packages/{pid}/status", {"status": "delivered"}, token=TOKEN1)

s, d = req("POST", "/reviews", {
    "sender_id": sid1, "traveler_id": tid2, "package_id": pid, "rating": 5, "comment": "Nice"
}, token=TOKEN1)
if s == 201:
    print(f"✅ [201] Review delivered package (Valid step)")
else:
    print(f"❌ Failed review: {d}")

s, d = req("POST", "/reviews", {
    "sender_id": sid1, "traveler_id": tid2, "package_id": pid, "rating": 4, "comment": "Again"
}, token=TOKEN1)
check_fail("Duplicate review for same package", s, d, 409)

# ─── Summary ───
print("\n" + "=" * 55)
print(f"  Edge Case Results: {PASS} passed  |  {FAIL} failed")
print("=" * 55 + "\n")

sys.exit(0 if FAIL == 0 else 1)
