# ハードウェア元データ

最新状態は [HANDOFF.md](../HANDOFF.md) と [control-r1記録](../docs/control-board-r1.md) を参照する。候補配置/配線まで作成した低電圧制御板と、TBDを含む全体回路図を分けて管理する。現物未照合・製造承認前。

| 正本/生成物 | 扱い |
| --- | --- |
| [schematic_design.py](schematic_design.py) | 全体回路の手編集元。端子接続、出典、リスク |
| [pcb/control_layout.json](pcb/control_layout.json) | 制御板の候補フットプリント、配置、配線条件、RTC禁止領域、種配線、シルク |
| [../enclosure/layout.json](../enclosure/layout.json) | 外形、厚み、穴、ケース・管・操作部・アンテナの共通寸法 |
| [schematic/generated/nixie-jjy-clock.kicad_pro](schematic/generated/nixie-jjy-clock.kicad_pro) | 全体11ページ・111部品。HV/モジュールは未確定を含む |
| [pcb/generated/control-board.kicad_pro](pcb/generated/control-board.kicad_pro) | 制御板6ページ・54部品と候補PCB。ERC/DRC/未配線/等価性の問題0 |
| [pcb/generated/board-generation.json](pcb/generated/board-generation.json) | 正本ハッシュ、ライブラリ識別子/ファイルハッシュ、配線取り込み履歴 |
| [pcb/generated/routing/](pcb/generated/routing/README.md) | 今回のDSN/SES/対応ハッシュの保存版。直接編集しない |
| [mechanical/generated/manifest.json](mechanical/generated/manifest.json) | 外形/厚み/穴だけの6枚。回路PCBではない |

管4枚とコロンの回路PCBは未配線。全体回路図111部品のうち54部品に候補フットプリントを割り当てた。現物を照合していないため、ライブラリの存在確認と全パッドのネット検査をフットプリント確定と混同しない。ソケット/管、Nano互換機、JJY端子2.5mm、HVモジュール、電池ホルダー極性、TO-92リード成形等はR04/R15で残す。

生成されたKiCadは直接編集せず、正本を変更して再生成する。回路図生成は通常のPython、PCB生成/読戻しはKiCadのPythonを使う。具体的なコマンドは [HANDOFF.md](../HANDOFF.md) に集約する。検査出力は `build/phase2/` と `build/control-board/`。手元の一時ログはGitに入れず、引き継ぎに必要な検査スナップショットを `docs/validation/` に保存する。

制御板のJ41は既製降圧器からの5V入力、J42はHV/コロンの論理制御出力。12V・HV_RAW・SHDNを制御板へ引き込んでいない。装置全体のGNDは共通であり、ガルバニック絶縁はない。高電圧の部品定格・保護・放電・接触防止は未解決。
