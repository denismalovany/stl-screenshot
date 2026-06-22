# STL Screenshot

Drop an STL — get a beautiful PNG. One-click 3D model rendering with diffuse lighting.

<p align="center">
  <i>Add files → pick output folder → hit Render → done</i>
</p>

<p align="center">
  <a href="https://github.com/denismalovany/stl-screenshot/releases/latest"><img src="https://img.shields.io/github/v/release/denismalovany/stl-screenshot?label=latest" alt="release"></a>
  <a href="https://github.com/denismalovany/stl-screenshot/actions"><img src="https://img.shields.io/github/actions/workflow/status/denismalovany/stl-screenshot/build.yml" alt="build"></a>
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="platforms">
</p>

## ⚡ Quick Start

1. **Download** the binary for your OS from [Releases](https://github.com/denismalovany/stl-screenshot/releases/latest)
2. **Run it** — no installation, no Python, no dependencies
3. **Add** STL files, **pick** output folder, **click** Render

| Platform | File |
|---|---|
| 🪟 Windows | `STL-Screenshot-Windows.exe` |
| 🍎 macOS | `STL-Screenshot-macOS.zip` (unzip & run `.app`) |
| 🐧 Linux | `STL-Screenshot-Linux` (`chmod +x` first) |

> 💡 The binaries are fully self-contained — Python and all libraries are bundled inside.
> [OpenSCAD](https://openscad.org/) is only needed for CAD-style rendering. If it's not installed, the option simply won't appear in the UI, and everything works via the built-in `trimesh` engine.

## 🎨 Features

- 🌐 **EN / UA language toggle** — switch anytime
- **8 view angles**: iso, front, back, left, right, top, bottom, iso2
- **Two engines**: 
  - `trimesh` — built-in, always available. Diffuse lighting (face-normal shading), custom colors, tight cropping
  - `openscad` — optional, only appears if [OpenSCAD](https://openscad.org/) is installed. CAD-style rendering
- **Batch processing** — dozens of files at once
- **Mesh simplification** — for large models (200+ MB STL files)
- **Clean GUI** built with CustomTkinter
- 🪟 🍎 🐧 **Cross-platform** — binaries for Windows, macOS, Linux

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

## 🏗 Building from source

```bash
pip install pyinstaller customtkinter trimesh matplotlib numpy Pillow fast-simplification
python build_exe.py
```

The built binary will be at `dist/STL Screenshot.exe`.

### Automated builds (GitHub Actions)

Every push to `master` triggers [GitHub Actions](https://github.com/denismalovany/stl-screenshot/actions) that build binaries for all three platforms. When a new release is published, the binaries are automatically attached.

## 📂 Project Structure

```
Stl To Img/
├── stl_screenshot.py          # CLI render script
├── stl_screenshot_gui.py      # GUI app
├── build_exe.py               # .exe build script
├── .github/workflows/build.yml # CI/CD: auto-build for Win/Mac/Linux
├── STL Screenshot.exe         # Pre-built standalone binary
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
- `pyinstaller` — binary bundling (build only)

## 📄 License

MIT
