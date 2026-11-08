# 開発環境とmacOS / Ubuntu引き継ぎ

## KiCad導入後の更新

利用者の導入後、KiCad **10.0.8** を検出。CLIは `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`、付属Pythonは `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3`。後者で `import pcbnew` と `GetBuildVersion()` を実行できた。通常のPython 3.13からのimportとは別の環境である。

`sch erc`、`sch export netlist/pdf/bom` のヘルプを確認して使用し、回路図11ページの読込と出力を検証した。PCBは付属SWIG APIで機械外形と穴を作成し読戻した。現在は制御板54部品の配置/配線とERC/DRC/回路図等価性の検査まで実施した。`git show 4e38a86:HANDOFF.md` と [control-r1記録](control-board-r1.md) を参照する。MCPを追加しなくても今回の作業を実行できた。

macOSのSWIGではwxアプリケーション初期化を行う。KiCad側のフォント設定/画像ハンドラーについて診断メッセージが出ることがあるが、終了コード、出力の存在、読戻しを別々に確認し、ログに残す。CLIの診断メッセージを成功の根拠にしない。

以下はPhase 1開始時の履歴で、現在のKiCad準備状況とは区別する。Arduino CLIとUbuntu実行は引き続き未確認。

導入後のCLI再検査は [environment-kicad-2026-11-08.json](environment-kicad-2026-11-08.json) に保存した。OpenSCADは2021.01の公式DMGを一時利用して実行検証した。常設導入はしておらず、再生成時は `OPENSCAD_CLI` またはPATHを使う。

## Phase 1開始時の環境履歴（2026-11-08）

実行結果：[環境記録JSON](environment-2026-11-08.json)。作業開始時のGitツリーは `LICENSE` のみで、既存変更はなかった。

| 項目 | 確認結果 |
| --- | --- |
| 実ホスト | macOS 15.7.4 / arm64。要求書にあるUbuntuの実機ではない |
| Python | 3.13.1、Git 2.39.5、curl利用可 |
| KiCad | PATH、標準のmacOS配置、確認した一般的な配置に見つからず。導入版のバージョンは取得できない |
| Python API | 現在のPythonでは `pcbnew` をimportするためのモジュールが見つからない |
| Arduino | `arduino-cli` は未検出。IDEのGUI起動・書き込み検査も未実施 |
| MCP | このセッションの公開ツール一覧にKiCad専用ツールはない。設定ファイル全体の検査・変更はしていない |

「PC内のあらゆる場所に未インストール」と断定する調査ではない。独自配置なら `KICAD_CLI` に実行ファイルを指定して再検査する。

## 共通の実行方法

```sh
python3 scripts/inspect_environment.py --output build/environment.json
python3 scripts/check_phase1.py
python3 scripts/fetch_references.py
```

Python 3.10以降の標準ライブラリのみを使用する。環境調査スクリプトはKiCadがなければ `null` を返す。終了コード0はKiCadの準備完了を意味しない。`KICAD_CLI` → PATH → macOS標準配置の順に探索する。環境記録にローカルパスが含まれるので、共有前に内容を確認する。

## KiCadの準備（移行先で確認する内容）

1. 両OSで同じメジャーバージョンを選ぶ。本プロジェクトの実施版は10.0.8。調査時の[公式macOS配布ページ](https://www.kicad.org/download/macos/)は10.0.8を掲載していたが、CLIでプロジェクトを読込み、回路図と制御PCBの検査/出力を実行済み。GUIでの対話操作やUbuntu実行を検証した意味ではない。
2. macOSは公式配布を使う。Ubuntuは[公式Linux配布案内](https://www.kicad.org/download/linux-distros/)から対象Ubuntuに対応する配布経路を選ぶ。ディストリビューションの既定パッケージと別の版を混在させない。
3. シンボル、フットプリント、3Dモデルも同じ配布系列で導入する。部品ライブラリの名前・パッケージを実際に検索してから登録する。
4. スクリプトを再実行し、実際の `--version` と `--help` を保存する。次に `sch erc`、`pcb drc`、`sch export netlist`、`pcb export gerbers`、`pcb export drill` のヘルプを導入版で確認する。
5. 小さな試験プロジェクトで読込・保存・ERC/DRC・出力を検証する。現在は本プロジェクトの回路図/制御PCBでmacOSのCLI検査を実施済み。

[公式CLI資料](https://docs.kicad.org/10.0/en/cli/cli.html)で上記のコマンド系統は確認済み。CLIは主として検査・出力用であり、対話的な部品配置・配線作業のすべてを置き換えるものではない。生成スクリプトやMCPを使った場合もKiCadで読込み直し、公式CLIの結果を別途保存する。

## Arduinoの準備

[Arduino CLI公式導入資料](https://docs.arduino.cc/arduino-cli/installation/)またはArduino IDE 2系を使う。候補はクラシックNano相当のATmega328P、5V、16MHz。Nano Every、Nano ESP32、Nano R4、LGT8F328P搭載品等を同じ基板・コアとみなさない。

後工程でArduino AVR Boardsの版を固定し、`arduino:avr:nano:cpu=atmega328` または実機に合わせた `cpu=atmega328old` を記録する。これは[公式コアのboards.txt](https://github.com/arduino/ArduinoCore-avr/blob/master/boards.txt)と[旧ブートローダーの説明](https://support.arduino.cc/hc/en-us/articles/4401874304274-Select-the-right-processor-for-Arduino-Nano)で存在を確認した識別子で、まだコンパイルを実行していない。

互換機はUSBシリアルICとブートローダーが販売品で異なる。USBケーブル、ドライバー、Ubuntuのシリアルデバイス権限は実際の書き込み環境で確認する。相対パスを使い、ポート名を `/dev/ttyUSB0` やmacOSの特定名に固定しない。

## KiCad MCP（任意）

Phase 1では不要。必要になるのはKiCadのGUI/API経由で図面や配置を操作する経路を選ぶ時点。[候補プロジェクト](https://github.com/mixelpixx/KiCAD-MCP-Server)は公式KiCadとは別の外部ツールである。

調査した `stable` のcommitは `1d204fe3384eb73c890bbe531538a6e735c40fe0`。READMEにはLinux/macOSのセットアップ、Python/TypeScript構成、SWIGと実験的IPC経路の記載があった。対応範囲は変わるので、この記載を接続実績とはしない。

導入する場合は、先にKiCad単体を動かし、導入版に合うバックエンドとPython環境を確認する。外部サーバーはプロジェクト外の専用環境に固定し、MCPクライアントに登録する実行コマンド・作業ディレクトリ・環境変数を確認する。README内の一括インストールや設定書換えは内容を確認してから実行する。

接続後は実際のツール一覧とスキーマを列挙し、読み取りから試す。未接続のツール名やAPIを推測で呼び出さない。Claude Desktop用設定をCodexの設定として流用しない。今回はMCPの登録もOSへのインストールも行っていない。導入段階になったら必要な設定を利用者へ伝える。

## 引き継ぎ時に残すもの

- Gitの元データ、`AGENTS.md`、判断・出典・リスクの記録を引き継ぐ。`build/`、`.cache/` は各OSで再生成する。
- KiCad版・ライブラリ版、Arduinoコア版、ライブラリ版、ボード実型番、書き込み方式を環境記録へ追記する。
- KiCadは `${KIPRJMOD}` とプロジェクト内ライブラリを使い、`/Users/...` や `/home/...` の絶対パスを設計ファイルに埋め込まない。
- Ubuntuでは環境検査・資料取得・資料整合性検査を再実行する。現時点でUbuntu実機による可搬性検証は未実施。

## ローカル配線ツール

Freerouting 2.5.0 JARと一時配置したZulu Java 25で配線した。システムJava 14は変更していない。ツール本体は `.cache/` にありcloneには含まれない。`scripts/route_control_board.py` は公式JARのSHA-256を照合し、ローカル処理・解析データ送信無効・GUI/API/MCPサーバー無効で実行する。実行時の入力/出力ハッシュを記録し、KiCadで再検査する。必要なURL、版、パス、再開方法は `git show 4e38a86:HANDOFF.md` に集約した。Ubuntu上の実行は未検証。
