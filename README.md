# JJY対応4桁ニキシー管時計

IN-12B ×4で24時間の `HH:MM` を表示する卓上時計。JJY（40/60kHz）で補正し、受信できない間はDS3231で時刻を保持する設計です。Wi-Fi・GPS・インターネットは使いません。Arduino IDE / CLI向けのクラシックNano互換 ATmega328P 5V/16MHzを第一候補にしています。

**現在：回路図とケース案、制御・表示・コロン・電源の全4種の基板の候補配置・配線まで。製造承認前です。** 部品の現物照合、動くファームウェア、実測、Gerberは未完了です。

次の担当者は最初に [AGENTS.md](AGENTS.md)、[control-r1記録](docs/control-board-r1.md)、[リスク](docs/risks.md) を読んでください。2026-11-08時点の詳細な引き継ぎ資料（macOS/Ubuntuの再開コマンドを含む）は `git show 4e38a86:HANDOFF.md` で参照できます。

| 開くもの | 内容 |
| --- | --- |
| [制御板KiCadプロジェクト](hardware/pcb/generated/control-board.kicad_pro) | 6ページ・54部品。100×55mm・2層の候補PCBを同梱 |
| [全体KiCadプロジェクト](hardware/schematic/generated/nixie-jjy-clock.kicad_pro) | 11ページ・166部品。HVのTBD値と保留事項を含む |
| [OpenSCADケース](enclosure/clock.scad) | 濃色木枠と真鍮前面板の形状案。現物公差・保持具は未確定 |
| [共通寸法JSON](enclosure/layout.json) | 管中心/間隔、基板/穴、電源/操作、アンテナ、前面板の隙間の正本 |
| [control-r1記録](docs/control-board-r1.md) / [HV基板r1記録](docs/hv-boards-r1.md) | 実行結果、配線条件、コネクター、残る制約 |

2026-11-08、KiCad 10.0.8 / macOSで制御板のERC 0、DRC 0、未配線0、回路図等価性の問題0を確認しました。54部品＋取り付け穴4個、219パッドを回路図と照合しています。ERC/DRCは部品定格・実機安全性・受信性能・製造可否を保証しません。保存した記録は [docs/validation/](docs/validation/README.md) にあります。

## 資料

| 資料 | 内容 |
| --- | --- |
| [要求仕様](docs/requirements.md) / [実装計画](docs/implementation-plan.md) | 必須機能、受け入れ条件、今後の作業 |
| [部品調査](docs/components.md) / [概算BOM](docs/bom.csv) | 出典と電圧/端子、未見積の価格枠 |
| [回路構成](docs/architecture.md) / [判断記録](docs/decisions.md) | 構成比較、仮計算と変更理由 |
| [リスク](docs/risks.md) / [製造の状態](manufacturing/README.md) | HV・現物・電源・調達などの保留条件 |
| [ハードウェア](hardware/README.md) / [ケース](enclosure/README.md) | 正本と生成物、再生成方法 |
| [開発環境](docs/environment.md) / [資料台帳](docs/references/README.md) | ツール、任意MCP、一次資料URLと取得履歴 |
| [ファームウェア方針](firmware/README.md) / [検査計画](tests/README.md) | ピン割り当て、未実装機能と試験項目 |
| [Phase 1履歴](docs/verification.md) / [Phase 2初版履歴](docs/phase2-review.md) | 当時の実施結果。最新状態はcontrol-r1記録を優先 |

## 最初の確認

通常の資料スクリプトはPython 3.10以降の標準ライブラリのみを使います。PCBを扱うスクリプトはKiCad 10対応の `pcbnew` が使えるPythonで実行してください。macOS/Ubuntuの具体例は `git show 4e38a86:HANDOFF.md` の7〜8節にあります。

```sh
python3 scripts/inspect_environment.py --output build/environment.json
python3 scripts/check_phase1.py
python3 scripts/generate_schematic.py --check
python3 scripts/generate_schematic.py --variant control --check
python3 scripts/check_hardware.py
python3 scripts/generate_mechanical.py --check
```

KiCad MCPの設定は今回不要でした。公式CLIと実際に存在を確認したAPIで作成・検査しています。Ubuntu上の実行、Arduinoのコンパイル/書込は未実施です。

## ファイルの扱い

```text
AGENTS.md       AI向けの設計/検査/変更管理規約（CLAUDE.mdから参照）
docs/           要求、部品、出典、判断、リスク、保存した検査記録
hardware/       回路/配置の正本と生成済みKiCad、配線セッション
enclosure/      共通寸法JSONとOpenSCAD、生成定数
firmware/       Arduino向け方針（スケッチ未作成）
scripts/        生成、CLI検査、API読戻し、配線、資料検査
tests/          検査と将来のJJY擬似入力試験の計画
manufacturing/  未製造承認の状態と今後のリリース条件
build/          一時出力と検査ログ（Git対象外）
.cache/         外部PDF・一時ツール（Git対象外、cloneには含まれない）
```

AIが回路/基板/ソフトウェア/資料を担当し、人間が購入・実装・現物確認・実測・外装製作を担当します。電子回路の予算目標は15,000〜20,000円。現在の仮BOMは送料別15,315〜26,325円で、最新候補部品の個別見積は未取得です。
