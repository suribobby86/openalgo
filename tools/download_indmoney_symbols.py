"""Download INDmoney master contract symbols into OpenAlgo DB."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

# master_contract_db emits via socketio; stub it for CLI runs
import broker.indmoney.database.master_contract_db as mcdb

mcdb.socketio.emit = lambda *args, **kwargs: None

from broker.indmoney.database.master_contract_db import SymToken, master_contract_download


def main() -> None:
    before = SymToken.query.count()
    print(f"symtoken rows before: {before}")

    print("Starting INDmoney master contract download...")
    master_contract_download()

    after = SymToken.query.count()
    print(f"symtoken rows after: {after}")

    if after == 0:
        raise SystemExit("Download finished but symtoken table is still empty — check logs above.")

    nifty = SymToken.query.filter_by(symbol="NIFTY", exchange="NSE_INDEX").first()
    print("NIFTY index row:", "found" if nifty else "missing", f"(token={getattr(nifty, 'token', None)})")


if __name__ == "__main__":
    main()
