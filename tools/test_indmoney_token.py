"""One-off INDmoney token diagnostic. Does not print full tokens."""
import base64
import datetime
import json
import re
import sqlite3
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
DB_PATH = ROOT / "db" / "openalgo.db"


def load_env_token() -> str:
    text = ENV_PATH.read_text(encoding="utf-8")
    match = re.search(r"BROKER_API_SECRET\s*=\s*'([^']+)'", text)
    if not match:
        raise SystemExit("BROKER_API_SECRET not found in .env")
    return match.group(1)


def jwt_payload(token: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))


def main() -> None:
    env_token = load_env_token()
    payload = jwt_payload(env_token)
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = datetime.datetime.fromtimestamp(payload["exp"], datetime.timezone.utc)
    iat = datetime.datetime.fromtimestamp(payload["iat"], datetime.timezone.utc)

    print("=== .env token ===")
    print("tokenID:", payload.get("tokenID"), "partnerID:", payload.get("partnerID"))
    print("issued:", iat.isoformat())
    print("expires:", exp.isoformat())
    print("expired:", now > exp)

    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT user_id, broker, is_revoked, length(auth) FROM auth WHERE broker='indmoney'"
        ).fetchall()
        print("=== DB auth rows (indmoney) ===")
        print(rows if rows else "none")
        conn.close()
    else:
        print("=== DB not found ===")

    for label, headers in [
        ("raw Authorization", {"Authorization": env_token}),
        ("Bearer prefix", {"Authorization": f"Bearer {env_token}"}),
    ]:
        try:
            response = httpx.get(
                "https://api.indstocks.com/funds",
                headers=headers,
                timeout=30.0,
            )
            print(f"=== API test ({label}) ===")
            print("status:", response.status_code)
            print("body:", response.text[:250])
        except Exception as exc:
            print(f"=== API test ({label}) FAILED ===", exc)

    try:
        public_ip = httpx.get("https://api.ipify.org", timeout=10.0).text.strip()
        print("=== Your public IP (whitelist in INDstocks dashboard) ===")
        print(public_ip)
    except Exception as exc:
        print("IP lookup failed:", exc)


if __name__ == "__main__":
    main()
