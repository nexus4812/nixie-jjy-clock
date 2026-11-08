"""資料を取得し、取得時刻・URL・SHA-256を記録する。電子回路の妥当性は検証しない。"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import urllib.request


ROOT = Path(__file__).resolve().parents[1]


def retrieve(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": "nixie-jjy-clock-research/1.0"})
    with urllib.request.urlopen(request, timeout=25) as response:
        content = response.read()
        final_url = response.url
    if not content.startswith(b"%PDF-"):
        raise ValueError("PDFとして検証できない応答")
    temporary = destination.with_suffix(".tmp")
    temporary.write_bytes(content)
    temporary.replace(destination)
    return final_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, default=ROOT / "build/references/receipt.json")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    sources = json.loads((ROOT / "docs/references/sources.json").read_text(encoding="utf-8"))
    cache = ROOT / ".cache/references"
    cache.mkdir(parents=True, exist_ok=True)
    records = []
    for source in sources["sources"]:
        if not source.get("download"):
            continue
        destination = cache / (source["id"] + ".pdf")
        record = {
            "id": source["id"],
            "url": source["url"],
            "path": str(destination.relative_to(ROOT)),
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        try:
            cached = destination.exists() and not args.refresh
            if not cached:
                record["final_url"] = retrieve(source["url"], destination)
            content = destination.read_bytes()
            if not content.startswith(b"%PDF-"):
                raise ValueError("キャッシュがPDFではない")
            record.update({
                "status": "cached" if cached else "downloaded",
                "sha256": hashlib.sha256(content).hexdigest(),
                "bytes": len(content),
                "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            })
            print(f"{source['id']}: {record['status']} ({len(content)} bytes)")
        except Exception as error:
            record.update({"status": "failed", "error": str(error)})
            print(f"{source['id']}: failed: {error}", file=sys.stderr)
        records.append(record)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps({"records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if any(record["status"] == "failed" for record in records) else 0


if __name__ == "__main__":
    sys.exit(main())
