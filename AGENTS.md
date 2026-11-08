# 開発・設計規約

## 現在の作業範囲

- 最初に `README.md`、`docs/control-board-r1.md`、`docs/risks.md` を読む。2026-11-08時点の詳細な引き継ぎ資料は `git show 4e38a86:HANDOFF.md` で参照する。現状はPhase 2/3：全体回路図166部品、制御/表示/コロン/電源の全PCBの候補配置/配線とケースの並行設計（`docs/hv-boards-r1.md`）。成果物はレビュー用であり、製造承認ではない。
- 動くファームウェアは未作成。HV定数は計算上の候補で実測なし。最新記録は `docs/validation/`。過去のPhase 1/2初版記録は履歴として扱う。
- 回路図、PCB、Gerberを未作成・未検査のまま完成品として扱わない。
- 利用者の追加指定：macOS・Ubuntuで引き継げること。ファームウェアはArduino IDE / Arduino CLI向けを優先する。
- 利用者の追加指定：`enclosure/` にOpenSCAD設計を置く。管中心、基板外形/穴、端子/ボタン、アンテナ、前面板の隙間を `enclosure/layout.json` で共通管理する。現物照合までは暫定寸法とする。

## 根拠と変更管理

- 日本語で記述する。正式型番、端子名、KiCad識別子は原文を維持する。
- 事実・計算上の仮定・設計候補・実測済みを区別する。未確定事項には `docs/risks.md` のIDを付ける。
- 電気定格と端子配置は一次資料を優先し、`docs/references/sources.json` の資料ID・URL・ページを記録する。原メーカー不明の資料は明記する。
- OCRだけで高電圧部品のピン番号や寸法を確定しない。図の向き、原資料、実物を照合する。
- 部品の現物、ソケット、モジュールの派生版を照合するまでフットプリントを確定しない。
- 重要な設計変更は `docs/decisions.md` に理由と影響を記録する。指示なしにコミットやブランチ作成をしない。
- 既存の `LICENSE` は保持する。第三者資料やライブラリのライセンスを本リポジトリのライセンスと混同しない。

## 安全・検証

- 基板へ商用電源を持ち込まない。市販の絶縁された低電圧DCアダプターと既製昇圧モジュールを使う。
- 約180Vのアノードだけでなく、カソード、消灯時の端子、ハーネス、残留電荷も高電圧領域として扱う。
- 未定義BCD、595のOE、昇圧停止だけを感電防止・完全消灯の保証にしない。
- 定格、熱、絶縁距離、放電時間、物理カバーの確認をERC/DRCと別に管理する。
- 実行していないERC、DRC、ビルド、試験、実測を成功と記載しない。欠落ツールは失敗または未実施として報告する。
- 外形、穴、管間隔、製造用データの確定は各Phaseの完了条件を満たした後に行う。

## 可搬性とツール

- 補助スクリプトはPython 3.10以降の標準ライブラリを基本にする。パスは `pathlib`、外部コマンドは引数配列で扱う。
- GNU固有の `sed -i`、`readlink -f`、`sha256sum` や、Homebrew・aptの存在を前提にしない。
- KiCad CLIはPATH、環境変数 `KICAD_CLI`、macOS標準配置を順に確認する。API/オプションは導入版のヘルプ・公式資料で検証する。
- KiCadのメジャーバージョンをmacOS/Ubuntuで揃える。APIの存在を推測しない。MCPは任意で、公式CLIによる検証経路を残す。
- MCPやOSの設定を自動上書きしない。設定が必要になったら利用者へ必要な内容を伝える。
- 手編集元は `docs/`、`hardware/`、`firmware/`、`scripts/`、`tests/`。再生成物は `build/`、取得した資料は `.cache/references/` に分ける。
- `enclosure/` も手編集元。レビュー用KiCadとOpenSCADパラメーターは各 `generated/` に生成し、再現性確認のためGit管理する。生成物の直接編集はせず設計定義を変更する。
- 変更後は `python3 scripts/check_phase1.py` を実行する。これは資料整合性の検査であって回路検証ではない。
- 回路変更後は両variantの生成整合性と `check_hardware.py`、制御PCB変更後はKiCad Pythonで `check_control_board.py`、表示/コロン/電源PCB変更後は `check_hv_board.py` を実行する。DRCの `violations` だけでなく `unconnected_items` と `schematic_parity`、CLI終了コードを確認する。
- SESはDSN/SESハッシュの対応記録が一致するものだけ取り込む。自動配線結果の拡幅後もDRCを再実行する。DRCルールや除外を緩めて合格にしない。
- `docs/validation/` の保存済み実行記録と `hardware/pcb/generated/routing/` の配線保存版もGit管理する。ツール本体、外部PDF、個人設定は追加しない。
- 次回担当者向けの状態変更を `README.md` と `docs/` の該当資料に反映する。利用者は今回の引き継ぎ整理に対するcommit/pushを明示許可済み。将来の別作業への恒久的な許可とは解釈しない。
