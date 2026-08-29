# CursorBuilder

**한국어** · [English](README.en.md) · [日本語](README.ja.md)

A GUI tool for creating mouse cursors (**`.cur` / `.ani`**).
Reads cursors/images from a zip or folder, lets you set hotspots on the
preview, and converts them into multi-layer cursors.

## Features

- **Input source**: scans a zip or folder
  - `.cur` / `.ani` : processed as-is
  - Static images (`.png .jpg .bmp .ico .webp .tiff ...`) : converted to **`.cur`**
  - `.gif` : converted to **`.ani`** (frame durations preserved)
- **Hotspot setting** (4 methods)
  - Rectangle drag + centroid / tip / top-left corner
  - Manual point (click) — click the image to set a pixel-level hotspot
  - The selected area can be fine-tuned with **8 handles**, like resizing a window
- **Convert**: multi-layer `.cur` (16/24/32/48/64/96...) generation, `.ani` copy
- **i18n**: automatically follows the system locale
  (**한국어 / English / 日本語**), manual override available
- **Themes**: 16 modern 2020s-style themes, switchable in real time
  (bootstrap / catppuccin / tokyo-night / dracula / vapor / nord / gruvbox / one)

## Run

```bash
python -m pip install -r requirements.txt
python main.py
```

## Standalone Build (PyInstaller)

```bash
build.bat
# Output: dist/CursorBuilder.exe
```

An icon at `icons/app.ico` is applied automatically if present.

## Project Structure

```
cursorbuilder/
├── main.py               # Entry point (locale detect → theme → main window)
├── builder/              # Pure logic (GUI-independent)
│   ├── curio.py          # .cur parse/build
│   ├── anio.py           # .ani parse/build (RIFF/ACON)
│   ├── loader.py         # zip/folder scan + square-ize + GIF frames
│   ├── hotspot.py        # drag region → hotspot calc, proportional scaling
│   ├── output.py         # multi-layer .cur / .ani generation
│   └── i18n.py           # locale detect + translation dictionary
├── ui/main_window.py     # Tkinter + ttkbootstrap UI
├── locales/              # ko / en / ja translations
└── requirements.txt
```

## License

[Apache License 2.0](LICENSE)

> **Note**: Always check the original author's copyright and license terms
> before redistributing or modifying cursors. This tool is only for creating
> and converting cursors; it does not grant any rights to the cursor assets
> it processes.
