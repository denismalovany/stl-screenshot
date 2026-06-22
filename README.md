# STL Screenshot

Drop an STL — get a beautiful PNG. One-click 3D model rendering with proper lighting.

<p align="center">
  <i>Add files → pick output folder → hit Render → done</i>
</p>

## ⚡ Quick Start

1. **Download** `STL Screenshot.exe` from [Releases](https://github.com/user/stl-screenshot/releases)
2. **Run it** (Windows 10/11, **no installation required**)
3. **Add** STL files, **pick** output folder, **click** Render

> 💡 The `.exe` is fully self-contained — Python and all libraries are bundled inside.
> [OpenSCAD](https://openscad.org/) is only needed for CAD-style rendering. If it's not installed, the option simply won't appear in the UI, and everything works via the built-in `trimesh` engine.

## 🎨 Features

- **8 view angles**: iso, front, back, left, right, top, bottom, iso2
- **Two engines**: 
  - `trimesh` — built-in, always available. Diffuse lighting (face-normal shading), custom colors, tight cropping
  - `openscad` — optional, only appears if [OpenSCAD](https://openscad.org/) is installed. CAD-style rendering
- **Batch processing** — dozens of files at once
- **Mesh simplification** — for large models (200+ MB STL files)
- **Clean GUI** built with CustomTkinter

## 📸 Screenshots

_(add screenshots here)_

## 🖥 CLI Mode

```bash
pip install trimesh matplotlib numpy Pillow fast-simplification

# Single file
python stl_screenshot.py model.stl

# Batch with selected angles
python stl_screenshot.py "*.stl" --angles iso,front,top -o screenshots/ --tight-crop

# OpenSCAD with color scheme
python stl_screenshot.py model.stl --engine openscad --color-scheme Sunset

# High resolution
python stl_screenshot.py model.stl --width 3840 --height 2160 --color '#ff6633'
```

## 📋 CLI Options

| Flag | Default | Description |
|---|---|---|
| `--engine` | `trimesh` | `trimesh` or `openscad` |
| `--angles` | `iso` | Comma-separated view angles |
| `-o` / `--output` | next to source | Output file or directory |
| `--width`, `--height` | `1920`, `1080` | Output resolution |
| `--color` | `#3388cc` | Model color (hex) for trimesh |
| `--bg-color` | `white` | Background color for trimesh |
| `--tight-crop` | off | Tighter framing, less empty space |
| `--simplify` | `100000` | Max polygon count (0 = no simplification) |
| `--color-scheme` | `Metallic` | OpenSCAD color scheme |
| `-v` | off | Verbose output |

## 🏗 Building the .exe

```bash
pip install pyinstaller customtkinter
python build_exe.py
```

The built .exe will be at `dist/STL Screenshot.exe`.

## 📂 Project Structure

```
Stl To Img/
├── stl_screenshot.py       # CLI render script
├── stl_screenshot_gui.py   # GUI app
├── build_exe.py            # .exe build script
├── STL Screenshot.exe      # Pre-built standalone .exe
├── README.md
└── .gitignore
```

## 📦 Dependencies (for CLI / build)

- Python 3.10+
- `trimesh` — STL loading
- `matplotlib` — rendering with diffuse lighting
- `numpy` — math
- `Pillow` — image handling
- `fast-simplification` — mesh decimation
- `customtkinter` — GUI
- `pyinstaller` — .exe bundling (build only)

## 📄 License

MIT
