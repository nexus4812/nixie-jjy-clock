# ケース・基板の共通寸法設計

**`mechanical-r0`：配置検討用。現物照合前なので、木材・真鍮板の加工と基板発注には使わない。**

利用者の追加指定により、ケースと基板の機械設計を並行して進める。落ち着いた濃色木製ケース＋真鍮前面板を想定し、すべての配置寸法の正本を [layout.json](layout.json) に置く。

| ファイル | 扱い |
| --- | --- |
| [layout.json](layout.json) | 手編集する寸法・座標の正本。単位mm |
| [clock.scad](clock.scad) | 手編集するOpenSCAD形状。寸法は生成定数を参照 |
| [generated/layout.scad](generated/layout.scad) | JSONから生成。直接編集しない |
| `../hardware/mechanical/generated/` | 同じJSONから生成する基板外形と穴。部品/配線なし |
| `../build/enclosure/layout.svg` | 再生成可能な正面・上面の配置図 |
| `../build/enclosure/board-holes.csv` | 基板中心基準の穴一覧 |

## 暫定寸法

| 対象 | 初版の値 |
| --- | --- |
| ケース | 幅240 × 奥行110 × 高さ90mm、木枠10mm |
| 前面板 | 真鍮1.5mm。管外形は21×31mmの簡略包絡 |
| 管中心 | X=-63、-21、21、63mm、Z=48mm。等ピッチ42mm |
| 管窓 | 23×33mm、左右/上下に片側1mmの予約隙間 |
| 管の出 | ガラス前端Y=-3mm、真鍮表面Y=-1.5mmから1.5mm出る案 |
| 表示子基板 | 各34×54×1.6mm、Y=40mm、穴4個φ3.2mm |
| 制御基板 | 100×55×1.6mm、中心(-45,72,16)mm、穴4個φ3.2mm |
| コロン基板 | 14×42×1.6mm、中心(0,30,48)mm、穴2個φ2.2mm |
| 背面ボタン | X=-35、-15、5mm、Z=42mm、穴φ7mmを仮置き |
| 背面電源端子 | X=75mm、Z=55mm、穴φ8mmを仮置き |
| 背面JJY状態LED | X=35mm、Z=42mm、穴φ3.2mmを仮置き |
| アンテナ | 中心(-75,88,70)mm、X方向60mm×φ10mm |
| HVモジュール予約枠 | 中心(78,75,22)mm、50×35×20mm。実部品寸法ではない |

OpenSCADではXが左右、Yが奥行、Zが高さ。原点はケース幅中央・前面板裏・ケース底。Yは奥へ正、前面板はY=-1.5〜0mm。管の中心Xと表示子基板の中心Xは同じ計算式で導出する。管の奥行35mmとソケット積層8mmから基板面Y=40mmを算出するが、ソケットの現物高さは未確認。

基板の穴は中心基準で管理する。KiCadの外形は左上(0,0)を原点とし、穴を `(幅/2 + 中心基準X, 高さ/2 - 中心基準Y)` に変換する。XZ板の中心基準Yは上方向のZ、XY板では奥行方向。裏面から見た左右を混同しない。

## 生成・検査

macOS/Ubuntu共通：

```sh
python3 scripts/generate_mechanical.py
python3 scripts/generate_mechanical.py --check
```

基板外形の生成/読戻し照合は `pcbnew` をimportできるKiCadのPythonで実行する。現在のmacOSでは次を使用する。Ubuntuは導入版に対応するPythonを環境確認後に使う。

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 scripts/generate_board_envelopes.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 scripts/check_board_envelopes.py
```

機械用基板は各ボードの外形、板厚、非めっき取り付け穴のみ。回路図からの部品配置/配線基板に見せかけず、後工程で統合・再照合する。

## OpenSCADで開く

`clock.scad` を開いてF5で組立を確認する。`part` は `assembly`、`front`、`rear`、`shell`、`hv_cover`、`front_2d`、`rear_2d` を選べる。`exploded` で前後板を離し、`show_internal` で基板・アンテナ・HV予約枠を表示する。

管は原資料の外形を簡略化した包絡で、内部電極の3Dモデルではない。`show_digit_preview` の1234は見た目の確認用。2021.01でCSG/SVG/STL/PNG出力を実行検証したが、材料・固定方法・公差まで検証した製造モデルではない。

導入済みCLIの `OPENSCAD_CLI` を指定して `python3 scripts/check_enclosure.py --preview` を実行すると、構文・出力と2D XMLを検査し、ログと組立画像を `build/enclosure/` に保存する。macOSでは未導入だったため公式DMGを一時利用して検査した。常設して再生成する場合は [公式配布](https://openscad.org/downloads.html) から導入する。MCP設定は不要。

CLIを導入している環境では、まずその版の `--help` を確認してから、例として `openscad -o build/enclosure/front.svg -D 'part="front_2d"' enclosure/clock.scad` で2D形状を出力する。2D出力も現段階では加工指示ではない。

## 未確定事項

- 各管・ソケット・Nano互換機・HVモジュール・ネオン・スイッチ・DCジャックの現物と公差を未照合。予約枠と実寸を区別する。
- 管の保持治具、ソケットの固定、板の脱着、木枠と真鍮板の締結、木材の伸縮、ボタン本体の外形、ストレインリリーフは未確定。
- HVモジュールのカバー形状は概念モデル。固定爪、通気、耐熱性、表示子/ハーネスの絶縁カバーまで完成していない。木枠や3Dモデルがあるだけで感電防止を保証しない。
- アンテナとHV予約枠の包絡間距離は約103.4mm。配置比較の指標であり、受信を保証する距離ではない。MCU・USB・降圧器の雑音と真鍮板の影響を別に評価する。
- 公称1mmの管窓隙間は公差を含まない。金属板によるガラスへの荷重や、接触・絶縁の合否を実物で確認する。

管間隔を変更するときはJSONの `tube.pitch` を変更して再生成・照合する。基板穴やボタン位置をSCADとKiCadで別々に直さない。

## control-r1との接続

[低電圧制御板](../hardware/pcb/generated/control-board.kicad_pcb) は共通JSONの制御板外形100×55mm、厚み1.6mm、穴4個を使って候補配置/配線済み。`hardware/mechanical/generated/control.kicad_pcb` は機械用の別ファイルであり、回路基板は `hardware/pcb/generated/control-board.kicad_pcb`。ケースの部品包絡は簡略モデルのままで、Nano/USB/ソケット/電池/ヘッダー/ハーネスの実高さや挿抜空間の検査は今後行う。今回、共通寸法そのものは変更していない。
