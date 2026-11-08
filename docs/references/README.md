# 出典と資料取得

資料ID・URL・一次/二次の区分・参照箇所は [sources.json](sources.json) が正本。技術資料、販売ページ、操作方法を分けて記録している。価格・在庫・公開版は2026-11-08の確認であり、発注時に再確認する。

## オフライン資料

```sh
python3 scripts/fetch_references.py
```

`download: true` のPDFだけを `.cache/references/S01.pdf` 等へ取得する。生成される `build/references/receipt.json` にURL、取得/キャッシュ/失敗、確認時刻、バイト数、SHA-256を記録する。PDFヘッダーの確認までで、全ページの読解や定格照合を自動化するものではない。

初回調査の取得記録は [retrieval-2026-11-08.json](retrieval-2026-11-08.json)。現環境での通信失敗も残す。キャッシュの確認時刻は初回取得日時を保証しない。同じURLの資料が更新される可能性があるため、再設計時にはハッシュと版を比較する。

PDF本体は再配布条件が未確認のためGitに入れない。Ubuntu移行後は再取得する。再取得できない資料があれば供給元に問い合わせ、出所不明の置換やTLS検証の無効化で埋めない。ブラウザー経由で閲覧できた事実と、スクリプトでローカルに保存できた事実も区別する。

## 優先して参照する資料

| ID | 資料 | 使用目的 |
| --- | --- | --- |
| S01 / S02 | [IN-12B原資料](https://www.tube-tester.com/sites/nixie/dat_arch/IN-12A_IN-12B_03.pdf) / [英訳](https://download.mikroe.com/documents/datasheets/Nixie_IN-12B_datasheet.pdf) | 始動・電源・電流・図中端子。翻訳は補助 |
| S03 | [K155ID1配布資料](https://eandc.ru/pdf/mikroskhema/k155id1.pdf) | 端子、TTL負荷、非選択出力の注意。原メーカー未特定 |
| S04 / S05 | [TI HCT595](https://www.ti.com/lit/ds/symlink/sn74hct595.pdf) / [Nexperia HC/HCT595](https://assets.nexperia.com/documents/data-sheet/74HC_HCT595.pdf) | 入出力の互換性。採用メーカーの定格を使う |
| S06 | [Analog Devices DS3231](https://www.analog.com/media/en/technical-documentation/data-sheets/DS3231.pdf) | RTC電源・端子・バックアップ・状態ビット |
| S07 / S08 / S09 | [aitendo販売ページ](https://www.aitendo.com/product/21528) / [モジュール仕様](https://aitendo3.sakura.ne.jp/aitendo_data/product_img/test/RCCM-6181B-JJY/RCCM-6181B-JJY.pdf) / [MAS6181B](https://www.mas-oy.com/wp-content/uploads/2016/05/da6181B.pdf) | 電圧表記の矛盾、選局、OUT極性・出力能力 |
| S10 / S11 | [NICT送信方法](https://jjy.nict.go.jp/jjy/trans/index.html) / [時刻符号](https://www.nict.go.jp/sts/jjy_signal.html) | JJY復号と試験の基準 |
| S12 | [NCH6100HV設計者資料](https://nixieclock.org/wp-content/uploads/2020/02/NIXIE-Power-Supply-Datasheet-EN-v1.0.0.pdf) | 昇圧仕様とSHDN。現物との一致は未確認 |
| S13 / S14 | [Arduino Nano](https://docs.arduino.cc/resources/datasheets/A000005-datasheet.pdf) / [ピン表](https://docs.arduino.cc/resources/pinouts/A000005-full-pinout.pdf) | クラシックNanoの基準。互換機の保証ではない |
| S32 | [TI HCT125](https://www.ti.com/lit/ds/symlink/sn74hct125.pdf) | JJY出力3Vから5Vへのバッファ候補 |

その他の電源、ネオン、比較価格、KiCad、MCP、Arduino CLI、既存公開設計は台帳に記録した。参考Etsyページ（S31）は取得エラーのため、外観の細部を確認したとは扱わない。

control-r1追加のS37〜S41はローカル配線ツール、KiCad標準ライブラリの利用条件、電池ホルダー候補と一時Javaの出典。外部ツール本体/PDFはGitへ追加せず、使用版/ハッシュと検査結果を `git show 4e38a86:HANDOFF.md` と `docs/validation/` に保存する。
