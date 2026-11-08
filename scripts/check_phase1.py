"""Phase 1資料のリンク・出典・BOMを検査する。ERC/DRCや安全性の検査ではない。"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]


def check(require_downloads=False):
    errors = []
    required = [
        "README.md", "AGENTS.md", "docs/control-board-r1.md", "docs/validation/README.md", "docs/requirements.md", "docs/components.md",
        "docs/architecture.md", "docs/bom.csv", "docs/risks.md",
        "docs/environment.md", "docs/implementation-plan.md", "docs/decisions.md",
        "docs/verification.md", "docs/references/README.md", "hardware/README.md",
        "firmware/README.md", "tests/README.md", "manufacturing/README.md",
    ]
    for relative in required:
        if not (ROOT / relative).is_file():
            errors.append(f"必須資料なし: {relative}")
    manifest = json.loads((ROOT / "docs/references/sources.json").read_text(encoding="utf-8"))
    sources = {source["id"]: source for source in manifest["sources"]}
    if len(sources) != len(manifest["sources"]):
        errors.append("出典IDの重複")
    for source in sources.values():
        if not source["url"].startswith("https://") or not source.get("locator"):
            errors.append(f"出典URL/参照箇所が不足: {source['id']}")
    markdown_files = [ROOT / "README.md", ROOT / "AGENTS.md"]
    for directory in ("docs", "hardware", "enclosure", "firmware", "tests", "manufacturing"):
        markdown_files.extend((ROOT / directory).rglob("*.md"))
    for document in markdown_files:
        if not document.exists():
            continue
        content = document.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            parsed = urlparse(target)
            if not parsed.scheme and parsed.path:
                destination = document.parent / unquote(parsed.path)
                if not destination.exists():
                    errors.append(f"リンク先なし: {document.relative_to(ROOT)} -> {target}")
        for source_id in set(re.findall(r"\bS\d{2}\b", content)):
            if source_id not in sources:
                errors.append(f"出典IDなし: {document.relative_to(ROOT)} -> {source_id}")
    with (ROOT / "docs/bom.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    item_ids = set()
    totals = {"circuit_low": 0, "circuit_high": 0, "shipping_low": 0, "shipping_high": 0}
    for row in rows:
        item_id = row["item_id"]
        if item_id in item_ids:
            errors.append(f"BOM ID重複: {item_id}")
        item_ids.add(item_id)
        quantity = int(row["quantity"])
        low = int(row["unit_low_jpy"])
        high = int(row["unit_high_jpy"])
        if quantity <= 0 or low < 0 or low > high:
            errors.append(f"BOM数値不正: {item_id}")
        if row["price_kind"] not in ("observed", "budget"):
            errors.append(f"価格区分不正: {item_id}")
        if row["price_kind"] == "observed" and (low != high or not row["source_ids"]):
            errors.append(f"実売確認価格の根拠不足: {item_id}")
        for source_id in filter(None, row["source_ids"].split(";")):
            if source_id not in sources:
                errors.append(f"BOM出典IDなし: {item_id} -> {source_id}")
        category = "shipping" if item_id == "B21" else "circuit"
        totals[category + "_low"] += quantity * low
        totals[category + "_high"] += quantity * high
    totals["all_low"] = totals["circuit_low"] + totals["shipping_low"]
    totals["all_high"] = totals["circuit_high"] + totals["shipping_high"]
    receipt_path = ROOT / "docs/references/retrieval-2026-11-08.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {"records": []}
    for record in receipt["records"]:
        source_id = record["id"]
        if source_id not in sources or record["url"] != sources[source_id]["url"]:
            errors.append(f"取得記録と資料台帳の不一致: {source_id}")
        if record["status"] in ("downloaded", "cached"):
            expected_hash = record.get("sha256", "")
            if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
                errors.append(f"取得ハッシュ不正: {source_id}")
            cached_path = ROOT / ".cache/references" / (source_id + ".pdf")
            if cached_path.exists() and hashlib.sha256(cached_path.read_bytes()).hexdigest() != expected_hash:
                errors.append(f"キャッシュと取得ハッシュの不一致: {source_id}")
    acquired = {record["id"] for record in receipt["records"] if record["status"] in ("downloaded", "cached")}
    missing = sorted(source_id for source_id, source in sources.items() if source["download"] and source_id not in acquired)
    if require_downloads and missing:
        errors.append("ローカル未取得資料: " + ", ".join(missing))
    return {
        "status": "FAIL" if errors else "PASS",
        "scope": "資料の整合性のみ。回路・安全性・Ubuntuでの実行は未検証。価格の実売再確認は行わない。",
        "source_count": len(sources),
        "bom_rows": len(rows),
        "budget_jpy": totals,
        "downloaded_receipt_count": len(acquired),
        "unavailable_downloads": missing,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-downloads", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = check(args.require_downloads)
    except (OSError, ValueError, TypeError, KeyError) as error:
        report = {"status": "FAIL", "errors": [str(error)]}
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
