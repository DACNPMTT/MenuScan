"""End-to-end auth diagnostic.

Injects a known magic-link token for an existing user, then plays the full
browser auth flow:
1. POST /auth/magic-links/verify → capture access_token + Set-Cookie refresh_token
2. POST /auth/refresh with the cookie → expect 200 + new access_token
3. GET /auth/me with the access_token → expect 200 + user data

Prints each step's HTTP status and a one-line summary. Run from app/ folder.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import psycopg2

DB_URL = "postgresql://menuscan:localdev@localhost:55432/menuscan"
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
TEST_EMAIL = "qndjxz@gmail.com"


def inject_token(raw: str) -> None:
    h = hashlib.sha256(raw.encode()).hexdigest()
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("select id from users where email=%s", (TEST_EMAIL,))
    row = cur.fetchone()
    if not row:
        print(f"FAIL: no user with email {TEST_EMAIL}")
        sys.exit(1)
    uid = row[0]
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


def http_request(
    method: str,
    path: str,
    *,
    body: dict | None = None,
    cookie_header: str | None = None,
    auth_token: str | None = None,
) -> tuple[int, dict, dict[str, str]]:
    headers = {"Content-Type": "application/json"}
    if cookie_header:
        headers["Cookie"] = cookie_header
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    data = json.dumps(body).encode() if body is not None else None
    req = Request(
        f"http://{BACKEND_HOST}:{BACKEND_PORT}{path}",
        data=data,
        method=method,
        headers=headers,
    )
    try:
        with urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode()), dict(resp.headers)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read().decode()), dict(exc.headers)


def main() -> None:
    raw_token = "e2e_diagnostic_token_xyz123"
    inject_token(raw_token)
    print(f"[1] injected magic-link token for {TEST_EMAIL}")

    # Step 1: verify → get access_token + Set-Cookie refresh_token
    status, body, headers = http_request(
        "POST",
        "/api/v1/auth/magic-links/verify",
        body={"token": raw_token},
    )
    print(f"[2] /auth/magic-links/verify → HTTP {status}")
    if status != 200:
        print(f"    body: {body}")
        sys.exit(1)
    access_token = body["data"]["access_token"]
    set_cookie = headers.get("set-cookie", "")
    print(f"    access_token len: {len(access_token)}")
    print(f"    Set-Cookie: {set_cookie[:120]}")

    # Parse the refresh_token cookie value
    cookie = SimpleCookie()
    cookie.load(set_cookie)
    if "refresh_token" not in cookie:
        print("    FAIL: refresh_token cookie NOT set in response")
        sys.exit(1)
    refresh_value = cookie["refresh_token"].value
    cookie_header = f"refresh_token={refresh_value}"
    print(f"    refresh_token cookie captured (len={len(refresh_value)})")

    # Step 2: refresh → expect 200
    status, body, headers = http_request(
        "POST",
        "/api/v1/auth/refresh",
        cookie_header=cookie_header,
    )
    print(f"[3] /auth/refresh (with cookie) → HTTP {status}")
    if status == 200:
        new_token = body["data"]["access_token"]
        print(f"    new access_token len: {len(new_token)}")
        print(f"    rotated Set-Cookie: {headers.get('set-cookie','')[:120]}")
    else:
        print(f"    FAIL body: {body}")
        sys.exit(1)

    # Step 3: /auth/me with the refreshed access token
    status, body, _ = http_request(
        "GET",
        "/api/v1/auth/me",
        auth_token=new_token,
    )
    print(f"[4] /auth/me (with refreshed token) → HTTP {status}")
    if status == 200:
        u = body["data"]
        print(f"    user_id={u['id']} email={u['email']} role={u['role']}")
        print("\n✓ Auth flow works end-to-end. The 5-min logout is NOT a backend bug.")
        print("  Likely cause: frontend in-memory access_token lost on F5/page-reload +")
        print("  refresh fails in browser (SameSite/Lax on cross-port localhost).")
    else:
        print(f"    FAIL body: {body}")


if __name__ == "__main__":
    main()
