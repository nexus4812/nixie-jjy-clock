"""制御板DSNをローカル配線し、SESと入力のSHA-256を対応付ける。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from mechanical import ROOT


JAR_SHA256 = "f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java", default=os.environ.get("JAVA_EXECUTABLE") or shutil.which("java"))
    parser.add_argument("--jar", type=Path, default=Path(os.environ.get("FREEROUTING_JAR", ROOT / ".cache/freerouting-2.5.0.jar")))
    parser.add_argument("--board", choices=["control", "display", "colon", "power"], default="control")
    args = parser.parse_args()
    if not args.java or not args.jar.is_file():
        parser.error("Java 25の実行ファイルとFreerouting 2.5.0 JARを--java/--jarで指定してください")
    if digest(args.jar) != JAR_SHA256:
        parser.error("公式2.5.0 JARのSHA-256と不一致")
    stem = args.board + "-board"
    directory = ROOT / "build" / stem
    directory.mkdir(parents=True, exist_ok=True)
    dsn = directory / (stem + ".dsn")
    session = directory / (stem + ".ses")
    receipt = directory / (stem + ".routing.json")
    if not dsn.is_file():
        parser.error("generate_control_board.pyによるDSN出力が先に必要です")
    version = subprocess.run([args.java, "-version"], capture_output=True, text=True, timeout=15)
    if version.returncode:
        parser.error("Javaの起動に失敗しました")
    # 以前の出力を今回の成功と取り違えない。
    session.unlink(missing_ok=True)
    receipt.unlink(missing_ok=True)
    command = [args.java, "-Xmx2g", "-jar", str(args.jar.resolve()),
               "-de", str(dsn), "-do", str(session), "-da",
               "--user_data_path=" + str(ROOT / "build/freerouting-jvm-data"),
               "--gui.enabled=false", "--api_server.enabled=false", "--mcp_server.enabled=false",
               "--router.autorouter.max_passes=80", "--router.optimizer.max_threads=2",
               "--router.optimizer.enabled=false", "--router.automatic_neckdown=true",
               "--router.fanout.enabled=true"]
    with (directory / "router-jvm.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    if result.returncode or not session.is_file() or not session.stat().st_size:
        raise RuntimeError("配線出力失敗。build/control-board/router-jvm.logを確認してください")
    record = {"status": "SES_GENERATED_REQUIRES_KICAD_DRC", "router": "Freerouting 2.5.0 JVM",
              "jar_sha256": digest(args.jar), "dsn_sha256": digest(dsn), "ses_sha256": digest(session),
              "java_version": (version.stdout + version.stderr).strip(), "command": command,
              "manufacturing_release": False}
    receipt.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("SESと入力ハッシュを保存。接続完了・線幅・間隔はKiCadで別途検査してください。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
