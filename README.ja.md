# CursorBuilder

**한국어** · [English](README.en.md) · [日本語](README.ja.md)

マウスカーソル(**`.cur` / `.ani`**)を作成するGUIツールです。
zipまたはフォルダ内のカーソル・画像を読み込み、プレビュー上でホットスポットを
指定し、マルチレイヤーカーソルに変換します。

## 主な機能

- **入力ソース**: zipまたはフォルダをスキャン
  - `.cur` / `.ani` : そのまま処理
  - 静止画像(`.png .jpg .bmp .ico .webp .tiff ...`) : **`.cur`** に変換
  - `.gif` : **`.ani`** に変換 (フレームごとの再生時間を反映)
- **ホットスポット指定** (4方式)
  - 矩形ドラッグ + 重心 / 先端 / 左上角
  - 直接指定 (クリック) — 画像をクリックしてピクセル単位で指定
  - 指定した領域はウィンドウのリサイズのように**8つのハンドル**で微調整
- **変換**: マルチレイヤー `.cur`(16/24/32/48/64/96...) 生成、`.ani` コピー
- **i18n**: システムロケールに応じて **한국어 / English / 日本語** を自動適用
  (手動切り替え可)
- **テーマ**: 2020年代風モダンテーマ16種をリアルタイム切り替え
  (bootstrap / catppuccin / tokyo-night / dracula / vapor / nord / gruvbox / one)

## 実行

```bash
python -m pip install -r requirements.txt
python main.py
```

## スタンドアロンビルド (PyInstaller)

```bash
build.bat
# 出力: dist/CursorBuilder.exe
```

`icons/app.ico` があればアイコンが自動適用されます。

## プロジェクト構成

```
cursorbuilder/
├── main.py               # エントリポイント (ロケール検出→テーマ→メインウィンドウ)
├── builder/              # 純粋ロジック (GUI非依存)
│   ├── curio.py          # .cur パース/ビルド
│   ├── anio.py           # .ani パース/ビルド (RIFF/ACON)
│   ├── loader.py         # zip/フォルダスキャン + 正方形化 + GIFフレーム抽出
│   ├── hotspot.py        # ドラッグ領域→ホットスポット計算、比例スケール
│   ├── output.py         # マルチレイヤー .cur / .ani 生成
│   └── i18n.py           # ロケール検出 + 翻訳辞書
├── ui/main_window.py     # Tkinter + ttkbootstrap UI
├── locales/              # ko / en / ja 翻訳
└── requirements.txt
```

## ライセンス

[Apache License 2.0](LICENSE)

> **注意**: カーソルを再配布・改変する際は、元の作者の著作権・ライセンス条項を
> 必ず確認してください。本ツールはカーソルの作成・変換のためのツールであり、
> 処理対象のカーソル資産に対する権利を付与するものではありません。
