"""Sync Fyers access token from nse_options_analyzer into OpenAlgo auth DB."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import httpx

from database.auth_db import Auth, db_session, decrypt_token, upsert_auth


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def load_access_token(repo_env: Path | None) -> str:
    token = os.getenv("FYERS_ACCESS_TOKEN", "").strip()
    if token:
        return token
    if repo_env and repo_env.is_file():
        token = _read_env_file(repo_env).get("FYERS_ACCESS_TOKEN", "").strip()
    if token:
        return token
    raise SystemExit("FYERS_ACCESS_TOKEN missing (pass via env or --repo-env)")


def verify_token(token: str, api_key: str) -> tuple[bool, str]:
    if not api_key:
        return False, "BROKER_API_KEY missing in OpenAlgo .env"
    headers = {"Authorization": f"{api_key}:{token}"}
    try:
        response = httpx.get(
            "https://api-t1.fyers.in/api/v3/profile",
            headers=headers,
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        return False, f"Fyers API request failed: {exc}"
    try:
        body = response.json()
    except ValueError:
        return False, f"Fyers API returned non-JSON (status {response.status_code})"
    if body.get("s") == "ok":
        fy_id = (body.get("data") or {}).get("fy_id") or "unknown"
        return True, f"Fyers profile OK (fy_id={fy_id})"
    message = body.get("message") or str(body)[:200]
    return False, f"Fyers API error: {message}"


def resolve_username(explicit: str | None) -> str:
    if explicit:
        return explicit.strip()
    env_user = os.getenv("OPENALGO_USERNAME", "").strip()
    if env_user:
        return env_user
    rows = Auth.query.filter_by(broker="fyers", is_revoked=False).all()
    if rows:
        return str(rows[0].name)
    try:
        from database.user_db import find_user_by_username

        user = find_user_by_username()
        if user and getattr(user, "username", None):
            return str(user.username)
    except Exception:
        pass
    raise SystemExit(
        "No OpenAlgo username — pass --username or log into OpenAlgo once"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Fyers token into OpenAlgo auth DB")
    parser.add_argument("--username", default=None, help="OpenAlgo login username")
    parser.add_argument("--repo-env", default=None, help="nse_options_analyzer .env path")
    args = parser.parse_args()

    repo_env = Path(args.repo_env) if args.repo_env else None
    token = load_access_token(repo_env)
    api_key = os.getenv("BROKER_API_KEY", "").strip()

    ok, msg = verify_token(token, api_key)
    print(f"Token verify: {msg}")
    if not ok:
        raise SystemExit(1)

    username = resolve_username(args.username)
    rows = Auth.query.filter_by(broker="fyers", is_revoked=False).all()
    targets = [r for r in rows if r.name == username] or rows

    if not targets:
        upsert_auth(username, token, "fyers", revoke=False)
        db_session.commit()
        print(f"Created fyers auth row for {username!r}")
        return

    updated = 0
    for row in targets:
        old = decrypt_token(row.auth) if row.auth else ""
        same = old == token
        print(f"Updating auth row name={row.name!r} same_token={same}")
        upsert_auth(
            name=row.name,
            auth_token=token,
            broker="fyers",
            feed_token=decrypt_token(row.feed_token) if row.feed_token else None,
            user_id=row.user_id,
            revoke=False,
        )
        updated += 1

    db_session.commit()
    print(f"Synced {updated} fyers auth row(s). Open http://127.0.0.1:5000/auth/resume-broker if needed.")

    try:
        from database.master_contract_status_db import init_broker_status
        from utils.auth_utils import async_master_contract_download, load_existing_master_contract, should_download_master_contract
        from threading import Thread

        init_broker_status("fyers")
        should_download, reason = should_download_master_contract("fyers")
        target = async_master_contract_download if should_download else load_existing_master_contract
        print(f"Master contracts: {'download' if should_download else 'cache reload'} ({reason})")
        Thread(target=target, args=("fyers",), daemon=True).start()
    except Exception as exc:
        print(f"Master contract kickoff skipped: {exc}")


if __name__ == "__main__":
    main()