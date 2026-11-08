# 引き継ぎ：JJY対応ニキシー管時計

更新：2026-11-08 / macOSでの作業終了時点。**次の担当者はこのファイル → AGENTS.md → docs/control-board-r1.md → docs/risks.md の順に読む。** 作業を続ける前に検査結果を読み、既存の成果物を初期化しない。

## 1. 利用者の目的・指定

- 本物のIN-12B ×4、交換可能なソケット、24時間 `HH:MM`。中央は橙色ネオン2灯を第一候補。
- JJY 40/60kHzで補正。DS3231＋バックアップ電池で保持し、受信失敗でも有効RTCで継続。未受信状態表示と手動時刻設定が必須。
- Wi-Fi、GPS、インターネット同期は使わない。市販の安全性を確認できる低電圧アダプターと既製HV昇圧器を使う。
- MCUはArduino IDE / CLIで開発できる構成を希望。クラシックNano互換 ATmega328P 5V/16MHzが候補。Raspberry Pi SBC、Pico、ESP32へ勝手に変更しない。
- macOSとUbuntuで引き継げるようにする。MCPは必要なら案内するが、現状は不要。ユーザーはKiCadを導入済み。
- 濃色の木枠＋真鍮前面板のケースも並行設計。OpenSCADを使用し、管中心/間隔、基板外形/穴、電源/ボタン、JJYアンテナ、前面板の隙間を `enclosure/layout.json` で共通管理する。外装の実製作は人間側。
- AIが設計/PCB/ソフトウェア/資料、人間が購入/実装/実測/ケース製作。日本語で報告し、正式型番/識別子は維持する。
- 電子回路の予算目標15,000〜20,000円。仮BOMは送料別15,315〜26,325円、送料込み16,315〜28,825円。達成した予算ではない。最新候補部品の見積は未取得。
- 最新の依頼は「作業を引き継ぎ用MDに全部まとめ、README/AGENTS等を整理し、コミットしてpush」。この整理を区切りとしており、新たな回路設計を続ける依頼ではない。

## 2. 現在地：できたものと残っているもの

| 対象 | 完了した範囲 | 残っている範囲 |
| --- | --- | --- |
| Phase 1 | 要求、部品/端子調査、出典、仮BOM、リスク、計画 | 個別販売品・現物・価格・供給ロットの確定 |
| 全体回路図 | KiCad 10、11ページ、111部品、432接続を定義/照合、資料基準106ピン確認、ERC 0 | HV電圧/保護/抵抗TBD、個別モジュール/コネクターの確定、全体定格評価 |
| 低電圧制御PCB | `control-r1`、100×55×1.6mm、2層、54部品＋M3穴4個。配置/配線、219パッド照合、ERC/DRC/未配線/等価性の問題0 | 全部品の現物照合、実装/通電/温度、部品高さ、信号/電源品質、受信雑音、最終製造条件 |
| HV表示/電源/コロン | 回路図上の検討案、表示子4枚＋コロンの機械外形 | 回路の安全条件の確定、実フットプリント、配置/配線/DRC。制御PCBだけで時計は作れない |
| ケース | 共通寸法JSON、OpenSCAD、概略配置図/穴表、CSG/SVG/STL/PNG出力確認 | 保持具/締結/ハーネス/独立カバー、公差、部品高さと挿抜、金属への絶縁、熱、実加工 |
| Arduino | ピン割り当てと実装/試験方針 | スケッチ・JJY復号器・RTC/表示/操作・自動試験・コンパイル/書込は未作成/未実施 |
| 製造 | 未承認の状態を明示、リリース条件 | Gerber/Excellon、発注BOM、JLCPCB見積/条件照合、実装/通電手順、実機試験 |

**ERC/DRC成功と部品定格・実機安全性・製造承認は別。`manufacturing_release` はfalseのまま。** 購入・発注・通電してよい完成設計として引き継がない。

## 3. 最初に開くファイル・正本

| ファイル | 意味 |
| --- | --- |
| [AGENTS.md](AGENTS.md) | AIの設計/検査/変更管理規約 |
| [hardware/pcb/generated/control-board.kicad_pro](hardware/pcb/generated/control-board.kicad_pro) | 制御板6ページの回路図と配置/配線済み候補PCB |
| [hardware/schematic/generated/nixie-jjy-clock.kicad_pro](hardware/schematic/generated/nixie-jjy-clock.kicad_pro) | 全体11ページ、HV未確定を含む接続検討図 |
| [hardware/schematic_design.py](hardware/schematic_design.py) | 全回路の手編集元。ピン、ネット、出典、リスク |
| [hardware/pcb/control_layout.json](hardware/pcb/control_layout.json) | 制御板の候補フットプリント、位置/回転、配線条件、RTC禁止領域、VBAT種配線、シルク |
| [enclosure/layout.json](enclosure/layout.json) | ケース/基板/管/穴/操作/アンテナの寸法正本 |
| [enclosure/clock.scad](enclosure/clock.scad) | ケース形状の手編集元。定数はJSONから生成 |
| [docs/control-board-r1.md](docs/control-board-r1.md) | 最新制御板の接続/検査/注意事項 |
| [docs/risks.md](docs/risks.md) | R01〜R16と閉じるための証拠 |
| [docs/validation/README.md](docs/validation/README.md) | 保存した実行記録とプレビューの説明 |

`generated/` は再生成物だが、レビュー/再現確認用にGit管理する。直接手編集しない。`hardware/mechanical/generated/*.kicad_pcb` は外形/板厚/穴だけの6枚。制御板の回路PCBは **`hardware/pcb/generated/control-board.kicad_pcb`** であり、機械用 `control.kicad_pcb` と取り違えない。

`build/` は一時出力、`.cache/` は外部PDF/ツールで、どちらもGit対象外。引き継ぎに必要な検査記録とDSN/SESは今回保存版をGitへ追加した。ツール本体や外部PDFは含めない。

## 4. 最新の検査結果と限界

2026-11-08、KiCad 10.0.8 / macOSで実行：

- 全体回路図：11ページ・111部品、432接続、資料基準106ピン、ERC違反0。XMLネットリスト、CSV BOM、PDFを出力/照合。候補フットプリント54部品。
- 制御板：6ページ・54部品、基板上58フットプリント（穴4含む）、219パッド、802配線セグメント＋64ビア＝866。最小線幅0.20mm。
- 制御板ERC 0、DRCの違反0、未配線0、`schematic_parity` の問題0。部品ID/値/配置/回転、パッドネット、100×55mm/厚1.6mm/穴、RTCの両面配線/ビア禁止領域を読戻し確認。
- DRCは既定で無視される5項目（courtyard欠落、ビア中心、tuning profile、footprint filter/type）の一覧を保存。全種類の検査を有効化したという意味ではない。明示のDRC除外で違反を隠していない。
- 共通寸法検査、OpenSCAD定数一致、機械基板6枚の外形/厚み/穴読戻しを実施。OpenSCAD 2021.01のCSG/前後板SVG/木枠・HVカバーSTL/組立PNG出力を確認。
- 管ピッチ不足、基板外の穴、HV近傍アンテナ、パネル外電源穴の4種の異常寸法を検出した履歴あり。製造承認を要求する検査は失敗する状態が正しい。

未実施：Ubuntu実行、Arduinoビルド/書込、実物とフットプリント/極性の照合、実装/通電、HV定格/過渡/放電/絶縁/熱、JJY40/60kHzの実受信、JLCPCBへの注文、ケース実加工。プレビューは実機写真ではない。

過去の [docs/verification.md](docs/verification.md) はPhase 1履歴、[docs/phase2-review.md](docs/phase2-review.md) は103部品/393接続のR0履歴。古い「KiCad未導入」「PCB未配線」「全フットプリント未割当」を現在の状態と解釈しない。

## 5. 電気構成・重要な割り当て

- 全体は共通GND。12Vアダプター→保護/既製HV、別の既製5V降圧器→制御板。制御PCBの配線は5V/3V/論理のみ。HV_RAW/12V/SHDNを載せていないが、ガルバニック絶縁ではない。
- U1/U2：Nexperia `74HCT595D`、SOIC-16。4桁静的BCD、OEはGND固定、D8は予備。ラッチ初期値が未定義なので、起動データ設定前にHVを許可しない。OEや未定義BCDを安全な消灯手段にしない。
- U3：`DS3231SN#`、SOIC-16W。VCC/I2Cは5V、CR2032は非充電。5〜12 N.C.と13 GNDをGNDへ、RSTへ外部プルアップなし。電池ホルダーはKeystone 1060候補。
- U4：`MCP1700-3002E/TO`、1=GND/2=VIN/3=VOUT。JJYへ3V。入力100Ω＋10µF、出力は有効容量1µF以上が必要。TO-92 Wideは2.54mmへリード成形する候補で、現物未照合。
- U5：`SN74HCT125D`、SOIC-14。µA級のJJY OUTを5Vロジックへ。受信OUTへプルアップ/LEDを付けない。PDN1/2はMPSA42のオープンコレクターで3Vへ変換し、論理反転が入る。初期H/Hで停止。
- NanoのD2=JJY、D3=RTC SQW、D4/D5=PDN1/PDN2引き下げ、D6=HV_ENABLE、D7=COLON_ENABLE、D9=LED、D10=595ラッチ、D11=MOSI、D13=SCK。A0/A1/A2=SET/+/−、A4/A5=SDA/SCL。D0/D1は書込用、D8/D12/A3/A6/A7等は未使用。詳細は `firmware/README.md`。
- 表示子0〜3は正面左→右。16bit表示語bit0〜3=時十、4〜7=時一、8〜11=分十、12〜15=分一。上位バイトを先に転送すればU2に分、U1に時。これは回路の割り当てで、ソフトウェア試験は未実施。
- J41：1=5V_BUCK、2=GND。JP1を外すと降圧器5Vと制御5Vを切り離す。USB逆給電は互換機の実回路確認待ち。
- J42：1=GND、2=HV_ENABLE、3=COLON_ENABLE。別板のドライバーへ渡す論理信号。
- J50〜J53：1=+5V、2=GND、3〜6=各桁BCD bit0〜3。表示板側J10〜J13と対応。
- J45：1=+3V_JJY、2=GND、3=PDN2、4=OUT_RAW、5=PDN1。制御板の2.54mmヘッダーから実モジュール2.5mm端子へハーネス変換する案。
- J40：1=GND、2=SET、3=PLUS、4=MINUS、5=LED_ANODE。ボタン/LEDはケース背面へ。J3=5V/GND/SDA/SCL、J4=3V/OUT_RAW/JJY_DATAの診断用ヘッダー。

## 6. 共通機械寸法（すべて暫定）

単位mm。OpenSCADのX=左右/Y=奥/Z=上、原点は幅中央・前面板裏・底。KiCadは各基板左上原点で、穴は共通JSONから変換する。

| 対象 | 現在の案 |
| --- | --- |
| ケース | 240×110×90、木枠10、真鍮前面1.5 |
| IN-12B | 中心X=-63/-21/21/63、ピッチ42、Z=48、ガラス前端Y=-3 |
| 管と前面板 | 前面板Y=-1.5〜0、管窓23×33、管包絡21×31、片側隙間1。公差未算入 |
| 表示板×4 | 34×54×1.6、Y=40、管中心と同じX、中心基準穴(±13,±23)、φ3.2 |
| 制御板 | 100×55×1.6、ケース内中心(-45,72,16)、穴φ3.2 |
| 制御板KiCad穴 | (4,4)/(96,4)/(4,51)/(96,51) |
| コロン板 | 14×42、中心(0,30,48)、M2穴。表示板との重なりを避け10mm前へ |
| 背面操作 | ボタンX=-35/-15/5・Z42、電源端子X75・Z55、LED X35・Z42 |
| アンテナ | 中心(-75,88,70)、長さ60×φ10 |
| HV予約枠 | 中心(78,75,22)、50×35×20。実モジュール寸法ではない |

アンテナとHV予約枠の包絡距離は約103.4mm。受信を保証する距離ではない。ケースの基板は簡略包絡で、制御板の実部品高さ・USB/ハーネス・挿抜空間は未反映。JSONを変更したらSCADと全基板の寸法を再生成/検査する。ケースとPCBを別々に寸法修正しない。

## 7. 開発環境・検査だけ再開する手順

実施ホスト：`/Users/my/Documents/nixie-jjy-clock`、macOS 15.7.4 arm64、zsh、Python 3.13.1。Git remoteは `git@github.com:nexus4812/nixie-jjy-clock.git`、branchは `main`。着手時はLICENSEと初期commit `379c615` のみ。今回の最新commitは `git log -1 --oneline` で確認する。

整理の最終確認中、空の `package.json`（`{}`）と `package-lock.json`（依存空）が未追跡で出現した。今回の設計作業では作成/参照しておらず、生成元は未確認。別作業の可能性があるため削除/上書き/コミットせずローカルに保持した。時計の生成/検査にNode/npmは不要。次の担当者も、この2ファイルだけでNodeプロジェクトと判断しない。

KiCad実施版：**10.0.8**。CLIと付属Pythonは別経路。

```sh
# macOS、リポジトリ直下で実行
export KICAD_CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
KICAD_PYTHON=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
python3 scripts/inspect_environment.py --output build/environment.json
python3 scripts/check_phase1.py
python3 scripts/generate_schematic.py --check
python3 scripts/generate_schematic.py --variant control --check
python3 scripts/check_hardware.py
python3 scripts/generate_mechanical.py --check
"$KICAD_PYTHON" scripts/check_board_envelopes.py
"$KICAD_PYTHON" scripts/check_control_board.py
```

通常のPythonでは `pcbnew` をimportできない。macOS付属Python3.9はPCB API用で、資料スクリプトの基準Python3.10以降とは区別する。macOSのAPIでは `scripts/kicad_runtime.py` がwx.Appを初期化する。画像ハンドラー重複やFontconfigの診断が出るが、CLI終了コード・レポート・実出力を判定し、診断を削除して成功扱いにしない。

Ubuntuでは同じKiCad 10系と対応ライブラリ/Pythonを準備し、最初に以下を実行する。現ホストでUbuntu実行が成功した記録はない。

```sh
kicad-cli --version
python3 -c 'import pcbnew; print(pcbnew.GetBuildVersion())'
python3 scripts/inspect_environment.py --output build/environment-ubuntu.json
# 上記importが成功するPythonを使う。通常の資料検査は上のmacOS例と同じ。
python3 scripts/check_board_envelopes.py
python3 scripts/check_control_board.py
```

KiCad CLIは `KICAD_CLI` → PATH → macOS標準配置を探索。フットプリントは `--footprints` → `KICAD_FOOTPRINT_DIR` → macOS標準配置 → `/usr/share/kicad/footprints`。flatpak等の独自配置は明示指定する。projectのfp-lib-tableは `${KICAD10_FOOTPRINT_DIR}` を使うので、導入版のライブラリ設定を確認する。MCP/ユーザー設定の自動上書きはしていない。

## 8. 回路・配置を変更して再生成する手順

**検査だけなら再配線もJavaも不要。** 下記は正本を変更するときだけ実行する。配置だけ生成すると、保存済みの配線PCBを未配線版で上書きするので、再配線/取り込みまで続けて行う。

```sh
python3 scripts/generate_schematic.py
python3 scripts/generate_schematic.py --variant control
mkdir -p build/control-board
"$KICAD_CLI" sch export netlist --format kicadxml -o build/control-board/control.xml hardware/pcb/generated/control-board.kicad_sch
"$KICAD_PYTHON" scripts/generate_control_board.py
python3 scripts/route_control_board.py --java /path/to/java25 --jar /path/to/freerouting-2.5.0.jar
"$KICAD_PYTHON" scripts/generate_control_board.py --session build/control-board/control-board.ses
"$KICAD_PYTHON" scripts/check_control_board.py
python3 scripts/check_hardware.py
```

- 回路図の両variantは同じ回路定義を使う。controlは `board=control` の54部品と必要な電源宣言だけを抽出する。
- 種配線はRTC VBATの5セグメント。RTC直下7.8×10.6mmは両面の配線/ビア禁止。パッドは許可、GNDベタは未作成。
- DRCクリアランス0.25、最小線幅0.20、通常幅0.25、ビア0.8/穴0.4、銅箔-外形0.5。HV用の絶縁ルールではない。
- 自動配線時は0.30mmの間隔を指定し、取り込み後に0.20mm未満を0.20mmへ拡幅。今回76セグメントを拡幅後、実際の銅箔をDRC再検査して0件を確認。ルーターの自己判定だけを信用しない。
- `route_control_board.py` はDSN/SESのSHA-256対応を記録し、取り込みで一致を要求。配置/接続/制約が違う古いSESは使えない。保存版は `hardware/pcb/generated/routing/`。
- DSN先頭には出力先の絶対パスが含まれる。clone先やライブラリ版を変えるとDSNハッシュが変わり、保存SESの再取り込みが拒否されることがある。その場合は再配線する。完成候補PCBを読む/検査するだけなら保存SESの取り込みは不要。
- KiCad 10のXMLとPCBでは、NC自動ネット名中の `/` と `{slash}` 表現に差がある。生成/検査側で正規化済み。NCネットを省略すると等価性警告が出るので消さない。Sources/OpenRisks等のシンボルフィールドもPCBへコピーする。
- 取り付け穴は標準 `MountingHole_3.2mm_M3` のライブラリIDを保持する。手作りの空IDはSESのcomponent名が空になり取り込み失敗を起こした。

## 9. 一時ツールと保存対象外のもの

- Freerouting：公式v2.5.0 JAR。取得元は [公式release](https://github.com/freerouting/freerouting/releases/tag/v2.5.0)、API asset `613070298`。実施時はGitHub直リンクがHTTP504のため、`https://api.github.com/repos/freerouting/freerouting/releases/assets/613070298?download=1` にAccept `application/octet-stream` で取得。
- JAR SHA-256：`f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7`。公式APIのdigestと照合済み。ローカルは `.cache/freerouting-2.5.0.jar`。wrapperも同じ値を要求する。
- Java：一時展開したZulu `25.38.109-ca-jre25.0.5.0.3-macosx_aarch64`。実行ファイルは `.cache/tools/zulu25/zulu25.38.109-ca-jre25.0.5.0.3-macosx_aarch64/Contents/Home/bin/java`。システムJava14は変更していない。
- Java取得URL：`https://cdn.azul.com/zulu/bin/zulu25.38.109-ca-jre25.0.5.0.3-macosx_aarch64.tar.gz`。取得物のSHA-256は `3179912faeec7ea0e53e6226dc8b518e600acbe00ff3779e9894af1148b3e8b2`（ローカル記録。上流公開チェックサムとの独立照合は未実施）。Ubuntuには対応OS/CPUのJavaを用意し、macOS版をコピーしない。
- 配線はローカルJVMのみ。解析データ送信、GUI、API/MCPサーバーを無効化。設定/ログは `build/freerouting-jvm-data/`。ルーター終了0/SES生成は接続完了・DRC合格を意味しない。
- Freerouting2.5.0のネイティブCLIはComponentOutlineのserialization未対応で失敗したため不採用。JVMで検査を通した。2.1.0も試したが採用版ではない。`.cache/` に試行物が残っていても混用しない。
- OpenSCADは常設導入していない。公式2021.01 DMGをSHA-256 `4e4568e19992636ba497c04bc2238399c92314fcb7bf75dc3632aa623ca3635e` と照合して一時利用し、アンマウント済み。`/Volumes/OpenSCAD/...` は現在有効なパスではない。再実行は導入済み `OPENSCAD_CLI` またはPATHを使う。
- PDF本体は `.cache/references/`、取得履歴は `docs/references/retrieval-2026-11-08.json`。一部HTTP拒否/証明書/通信問題あり。TLS無効化せず、`python3 scripts/fetch_references.py` と台帳で再確認する。
- PDF/SVG調査用PyMuPDFは `build/research-tools/` に一時導入。通常の検査スクリプトの依存ではなく、cloneに含めない。

## 10. 次の担当者が優先する作業

1. 現状の正本/検査を読み、上記コマンドで保存済みPCBを検査する。Ubuntuなら環境差を記録する。KiCad/MCPの新規構築からやり直す必要はない。
2. R01/R02/R06を先に整理する。IN-12B原資料の電源200V以上と希望170〜180Vの差、K155ID1の非選択出力60V制約/クランプ、モジュールの出荷版/SHDN/連続容量/過渡を根拠付きで比較する。TBD抵抗に適当な値を入れてHV配線へ進まない。資料S03は原メーカー不明で、代替ドライバー案を含める。
3. 管/ソケット、Nano互換、JJY、HV、電池ホルダー、コネクターの個別購入品と原図を特定。R04の1:1印刷/ピン向き/寸法/極性を人間の現物確認へつなぐ。JJY販売ページは準備中だったため調達成立と扱わない。
4. 制御板のレビューを行い、電源/リターン、局所デカップリング、JJY raw線の長さ、VBAT、USB、ハーネスの誤接続対策、実部品高さを評価。現在の自動配線は接続/幾何検査済みだがEMC/電源品質/量産性の最終配置ではない。
5. 共通寸法へ保持具/ねじ頭/スペーサー/管とソケット高さ/ケーブルを反映し、ケースと表示板を具体化する。木枠/真鍮/レジストを単独のHVバリアにしない。独立カバー/放電/保守を設計する。
6. ハードウェア割り当てに従ってArduinoスケッチを作る。JJYは純粋ロジックに分離し、擬似パルス/不正フレーム/連続2分の整合/年跨ぎ/パリティ/毎時15・45分/うるう秒/RTC OSF/I2C失敗/手動設定を試験する。フレーム先頭時刻を取得完了時刻として書き込み、1分遅れる誤りを避ける。
7. HVと現物の保留を閉じてから全基板の配置/配線/DRC、BOM照合、JLCPCB条件/見積、製造出力/別ビューアー、段階通電手順へ進む。受信/熱/放電/感電防止は人間の実測記録が必要。

設計判断は `docs/decisions.md`、未確定は `docs/risks.md`、出典は `docs/references/sources.json` へ追記する。実行していない試験を成功と記録しない。利用者は確認のために毎回作業を止めることを望んでいないので、承認済み範囲の可逆作業は進める。部品仕様/API/現物値を推測して埋めない。
