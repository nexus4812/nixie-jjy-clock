# 保存した検査記録

`2026-11-08/` は引き継ぎ時に実行した検査出力のスナップショット。通常の出力先 `build/` はGit対象外なので、別PCでも検査範囲と実結果を読めるようにここへ保存する。再実行結果と保存版を取り違えない。

| ファイル | 内容 |
| --- | --- |
| `phase1-check.json` | 資料/リンク/出典/BOM整合性 |
| `system-verification.json` / `system-cli-log.json` | 全体回路図ERC/XML/BOM/PDF照合 |
| `control-verification.json` / `control-cli-log.json` | 制御板の独立照合とCLI実行結果 |
| `control-erc.json` / `control-drc.json` | KiCadのERC/DRC/未配線/等価性の生レポート |
| `board-envelopes.json` | 機械基板6枚の読戻し記録 |
| `mechanical-check.json` | 共通寸法検査 |
| `openscad-check.json` | OpenSCADを一時利用して実施したCSG/SVG/STL/PNG出力の記録 |
| `release-guard.json` / `stale-session-check.json` | 製造承認拒否と古いSES拒否の検査 |
| `routing.svg` / `assembly.svg` | 検査した候補制御PCBの配線/実装図。製造図ではない |
| `enclosure.png` / `enclosure-layout.svg` | ケースの概念プレビュー。実機写真/加工図ではない |
| `schematic.pdf` / `system-bom.csv` | 全体回路図のレビュー出力。TBD・現物未照合あり |
| `checks.json` / `sha256.json` | 引き継ぎ検査のコマンド/終了結果と保存物ハッシュ |

レポート中に実施PCのパスが含まれる。clone先で同じパスを用意する必要はない。CLI終了コード、DRCの `violations`、`unconnected_items`、`schematic_parity` を併せて確認する。`manufacturing_release: false` は維持する。実測/Ubuntu/Arduinoの成功記録は存在しない。

KiCadのSVGとFreeroutingのSESは生成元の行末空白も保持する。内容ハッシュを保つために空白を手修正せず、`.gitattributes` でこの生成物だけGitの空白検査対象から外す。手編集する資料/スクリプトは通常どおり検査する。

配線のDSN/SESと対応記録は [hardware側の保存版](../../hardware/pcb/generated/routing/README.md)。外部ツール/PDFはGitに含めない。再開方法は [HANDOFF.md](../../HANDOFF.md)。
