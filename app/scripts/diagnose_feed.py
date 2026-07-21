"""End-to-end feed diagnostic using the user's actual session.

Restores a session for the test user, then calls /api/v1/feed with the
access_token to verify the dataset cache + scoring work end-to-end. Run from
app/ folder.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg2

DB_URL = "postgresql://menuscan:localdev@localhost:55432/menuscan"
BACKEND = "http://127.0.0.1:8000"
TEST_EMAIL = "qndjxz@gmail.com"


def get_access_token() -> str:
    """Inject a magic link + verify it to mint a fresh access token."""
    raw = "feed_diag_token_xyz"
    h = hashlib.sha256(raw.encode()).hexdigest()
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("select id from users where email=%s", (TEST_EMAIL,))
    uid = cur.fetchone()[0]
    cur.execute("delete from magic_link_tokens where email=%s", (TEST_EMAIL,))
    cur.execute(
        """
        insert into magic_link_tokens (id, email, user_id, token_hash, expires_at, consumed_at, created_at)
        values (gen_random_uuid(), %s, %s, %s, %s, NULL, %s)
        """,
        (
            TEST_EMAIL,
            uid,
            h,
            datetime.now(timezone.utc) + timedelta(minutes=15),
            datetime.now(timezone.utc),
        ),
    )
    conn.commit()
    conn.close()

    req = Request(
        f"{BACKEND}/api/v1/auth/magic-links/verify",
        data=json.dumps({"token": raw}).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req) as resp:
        body = json.loads(resp.read().decode())
    return body["data"]["access_token"]


def main() -> None:
    token = get_access_token()
    print(f"[1] got access_token (len={len(token)})")

    # The user's actual location from their screenshot
    req = Request(
        f"{BACKEND}/api/v1/feed?radius_km=100&limit=20",
        method="GET",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urlopen(req) as resp:
            body = json.loads(resp.read().decode())
    except HTTPError as exc:
        print(f"[2] /feed → HTTP {exc.code}")
        print(f"    body: {exc.read().decode()[:300]}")
        sys.exit(1)

    print("[2] /feed?radius_km=100 → HTTP 200")
    data = body["data"]
    print(f"    items: {len(data['items'])}")
    print(f"    total_available: {data['total_available']}")
    print(f"    location_source: {data['location_source']}")
    if data["items"]:
        for i, item in enumerate(data["items"][:3]):
            print(
                f"    #{i+1} source_id={item['source_id']} "
                f"name={item['name']!r} "
                f"distance={item.get('distance_km')} "
                f"score={item['score']:.1f} "
                f"type={item['type']}"
            )
    else:
        print("    !!! FEED IS EMPTY — see diagnostic below")
        # Investigate why
        import psycopg2
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("select user_id, lat, lng, source from user_locations")
        print(f"    user_locations: {cur.fetchall()}")
        cur.execute("select count(*) from user_restaurant_saves")
        print(f"    saves: {cur.fetchone()[0]}")
        cur.execute("select count(*) from user_restaurant_seen")
        print(f"    seen: {cur.fetchone()[0]}")
        from src.modules.feed_recommend.data_loader import load_restaurants, _reset_cache_for_tests
        _reset_cache_for_tests(None)
        r = load_restaurants()
        print(f"    dataset cache: {len(r)} restaurants")
        if r:
            from src.modules.feed_recommend.scoring import haversine_km
            cur.execute("select lat, lng from user_locations where user_id=(select id from users where email=%s)", (TEST_EMAIL,))
            loc = cur.fetchone()
            if loc:
                within = sum(1 for x in r if haversine_km(loc[0], loc[1], x.lat, x.lng) <= 100)
                print(f"    within 100km of user ({loc}): {within}")


if __name__ == "__main__":
    main()
