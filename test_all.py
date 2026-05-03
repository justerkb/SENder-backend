"""
Quick end-to-end test for all endpoints.
Run with:  python test_all.py
"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://localhost:8000"
PASS, FAIL = 0, 0


def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if data else {}
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
print("  SENder API — Full Endpoint Test")
print("=" * 55)

# ─── ROOT ────────────────────────────────────────────────
print("\n── Root ──")
s, d = req("GET", "/")
check("GET /", s, d, 200)

# ─── TRAVELERS ───────────────────────────────────────────
print("\n── Travelers ──")
s, d = req("POST", "/travelers", {
    "name": "Test Traveler", "email": "traveler@test.com",
    "phone": "+1-111-1111", "bio": "Test bio"
})
t = check("POST /travelers", s, d, 201)
tid = t["id"]

s, d = req("GET", "/travelers")
check("GET /travelers", s, d, 200)

s, d = req("GET", f"/travelers/{tid}")
check(f"GET /travelers/{tid}", s, d, 200)

s, d = req("PUT", f"/travelers/{tid}", {
    "name": "Updated Traveler", "email": "updated@test.com",
    "phone": "+1-222-2222", "bio": "Updated bio"
})
check(f"PUT /travelers/{tid}", s, d, 200)

s, d = req("PATCH", f"/travelers/{tid}", {"bio": "Patched bio"})
check(f"PATCH /travelers/{tid}", s, d, 200)

s, d = req("GET", "/travelers?search=Updated")
check("GET /travelers?search=Updated", s, d, 200)

# ─── SENDERS ─────────────────────────────────────────────
print("\n── Senders ──")
s, d = req("POST", "/senders", {
    "name": "Test Sender", "email": "sender@test.com",
    "phone": "+1-333-3333", "city": "New York"
})
snd = check("POST /senders", s, d, 201)
sid = snd["id"]

s, d = req("GET", "/senders")
check("GET /senders", s, d, 200)

s, d = req("GET", f"/senders/{sid}")
check(f"GET /senders/{sid}", s, d, 200)

s, d = req("PUT", f"/senders/{sid}", {
    "name": "Updated Sender", "email": "updated.sender@test.com",
    "phone": "+1-444-4444", "city": "Los Angeles"
})
check(f"PUT /senders/{sid}", s, d, 200)

s, d = req("PATCH", f"/senders/{sid}", {"city": "Chicago"})
check(f"PATCH /senders/{sid}", s, d, 200)

# ─── PACKAGES ────────────────────────────────────────────
print("\n── Packages ──")
s, d = req("POST", "/packages", {
    "sender_id": sid, "description": "Test package",
    "pickup_city": "New York", "delivery_city": "London",
    "weight_kg": 1.5, "size": "small", "reward": 50.0,
    "deadline": "2026-12-01", "status": "pending"
})
pkg = check("POST /packages", s, d, 201)
pid = pkg["id"]

s, d = req("GET", "/packages")
check("GET /packages", s, d, 200)

s, d = req("GET", f"/packages/{pid}")
check(f"GET /packages/{pid}", s, d, 200)

s, d = req("PUT", f"/packages/{pid}", {
    "sender_id": sid, "description": "Updated package",
    "pickup_city": "New York", "delivery_city": "Paris",
    "weight_kg": 2.0, "size": "medium", "reward": 75.0,
    "deadline": "2026-12-15", "status": "pending"
})
check(f"PUT /packages/{pid}", s, d, 200)

s, d = req("PATCH", f"/packages/{pid}", {"status": "accepted", "reward": 90.0})
check(f"PATCH /packages/{pid}", s, d, 200)

s, d = req("GET", "/packages?status=accepted")
check("GET /packages?status=accepted (filter)", s, d, 200)

s, d = req("GET", "/packages?pickup_city=New%20York")
check("GET /packages?pickup_city filter", s, d, 200)

# ─── TRIPS ───────────────────────────────────────────────
print("\n── Trips ──")
s, d = req("POST", "/trips", {
    "traveler_id": tid, "from_city": "New York", "to_city": "London",
    "departure_date": "2026-06-01", "arrival_date": "2026-06-02",
    "available_weight_kg": 5.0, "notes": "Test trip", "status": "open"
})
trp = check("POST /trips", s, d, 201)
trid = trp["id"]

s, d = req("GET", "/trips")
check("GET /trips", s, d, 200)

s, d = req("GET", f"/trips/{trid}")
check(f"GET /trips/{trid}", s, d, 200)

s, d = req("PUT", f"/trips/{trid}", {
    "traveler_id": tid, "from_city": "New York", "to_city": "Paris",
    "departure_date": "2026-07-01", "arrival_date": "2026-07-02",
    "available_weight_kg": 8.0, "notes": "Updated trip", "status": "open"
})
check(f"PUT /trips/{trid}", s, d, 200)

s, d = req("PATCH", f"/trips/{trid}", {"status": "full"})
check(f"PATCH /trips/{trid}", s, d, 200)

s, d = req("GET", "/trips?status=full")
check("GET /trips?status=full (filter)", s, d, 200)

# ─── REVIEWS ─────────────────────────────────────────────
print("\n── Reviews ──")
s, d = req("POST", "/reviews", {
    "sender_id": sid, "traveler_id": tid, "package_id": pid,
    "rating": 5, "comment": "Great delivery!"
})
rev = check("POST /reviews", s, d, 201)
rid = rev["id"]

s, d = req("GET", "/reviews")
check("GET /reviews (list all)", s, d, 200)

s, d = req("GET", f"/reviews/{rid}")
check(f"GET /reviews/{rid}", s, d, 200)

s, d = req("GET", f"/reviews/traveler/{tid}")
check(f"GET /reviews/traveler/{tid}", s, d, 200)

s, d = req("PUT", f"/reviews/{rid}", {"rating": 4, "comment": "Updated comment"})
check(f"PUT /reviews/{rid}", s, d, 200)

s, d = req("PATCH", f"/reviews/{rid}", {"comment": "Patched comment"})
check(f"PATCH /reviews/{rid}", s, d, 200)

# ─── DELETE (cleanup) ─────────────────────────────────────
print("\n── DELETE (cleanup) ──")
s, d = req("DELETE", f"/reviews/{rid}")
check(f"DELETE /reviews/{rid}", s, d, 204)

s, d = req("DELETE", f"/packages/{pid}")
check(f"DELETE /packages/{pid}", s, d, 204)

s, d = req("DELETE", f"/trips/{trid}")
check(f"DELETE /trips/{trid}", s, d, 204)

s, d = req("DELETE", f"/senders/{sid}")
check(f"DELETE /senders/{sid}", s, d, 204)

s, d = req("DELETE", f"/travelers/{tid}")
check(f"DELETE /travelers/{tid}", s, d, 204)

# ─── 404 tests ────────────────────────────────────────────
print("\n── 404 Not Found checks ──")
s, d = req("GET", "/travelers/99999")
check("GET /travelers/99999 (not found)", s, d, 404)

s, d = req("GET", "/packages/99999")
check("GET /packages/99999 (not found)", s, d, 404)

# ─── Summary ─────────────────────────────────────────────
print("\n" + "=" * 55)
print(f"  Results: {PASS} passed  |  {FAIL} failed")
print("=" * 55 + "\n")

sys.exit(0 if FAIL == 0 else 1)
