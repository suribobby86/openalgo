"""Sync INDmoney token from .env into OpenAlgo auth DB."""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load .env the same way OpenAlgo does
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import httpx

from database.auth_db import Auth, db_session, decrypt_token, upsert_auth


def load_env_token() -> str:
    token = os.getenv("BROKER_API_SECRET", "").strip()
    if not token:
        raise SystemExit("BROKER_API_SECRET missing in .env")
    return token


def verify_token(token: str) -> bool:
    response = httpx.get(
        "https://api.indstocks.com/funds",
        headers={"Authorization": token},
        timeout=30.0,
    )
    print("API verify status:", response.status_code)
    if response.status_code != 200:
        print("API body:", response.text[:200])
        return False
    print("API body:", response.text[:120], "...")
    return True


def main() -> None:
    env_token = load_env_token()
    if not verify_token(env_token):
        raise SystemExit("Token in .env is not accepted by INDmoney API")

    rows = Auth.query.filter_by(broker="indmoney", is_revoked=False).all()
    if not rows:
        print("No active indmoney auth row — connect broker in OpenAlgo UI first.")
        raise SystemExit(1)

    updated = 0
    for row in rows:
        old = decrypt_token(row.auth)
        same = old == env_token
        print(f"Updating auth row name={row.name!r} same_token={same}")
        upsert_auth(
            name=row.name,
            auth_token=env_token,
            broker="indmoney",
            feed_token=decrypt_token(row.feed_token) if row.feed_token else None,
            user_id=row.user_id,
            revoke=False,
        )
        updated += 1

    db_session.commit()
    print(f"Synced {updated} auth row(s) from .env. Restart OpenAlgo or reconnect broker.")


if __name__ == "__main__":
    main()
