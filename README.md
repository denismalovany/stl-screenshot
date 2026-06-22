# STL Screenshot

Приймайте STL — отримуйте красиві PNG. Автоматизоване рендеринг 3D моделей у скріншоти з правильним освітленням.

<p align="center">
  <i>Перетягніть STL → виберіть теку → натисніть «Рендерити» → готово</i>
</p>

## ⚡ Швидкий старт

1. **Завантажте** `STL Screenshot.exe` з [Releases](https://github.com/user/stl-screenshot/releases)
2. **Запустіть** (Windows 10/11, **нічого встановлювати не треба**)
3. **Додайте** STL файли, **виберіть** теку, **натисніть** «Рендерити»

> 💡 `.exe` — повністю самодостатній. Python, бібліотеки та залежності вже всередині.
> Єдине, що може знадобитися — [OpenSCAD](https://openscad.org/), якщо хочете використовувати CAD-стиль рендерингу. Якщо OpenSCAD не встановлений — опція просто не з'являється в інтерфейсі, і все працює через вбудований рушій `trimesh`.

## 🎨 Можливості

- **8 ракурсів**: iso, front, back, left, right, top, bottom, iso2
- **Два рушії**: 
  - `trimesh` — вбудований, завжди доступний. Гнучке освітлення (diffuse shading по нормалях), кольори, тісне кадрування
  - `openscad` — опціональний, з'являється тільки якщо встановлено [OpenSCAD](https://openscad.org/). CAD-стиль рендерингу
- **Пакетна обробка** — десятки файлів за раз
- **Спрощення сітки** — для великих моделей (200+ MB)
- **Зручний GUI** на CustomTkinter

## 🖥 Консольний режим

```bash
pip install trimesh matplotlib numpy Pillow fast-simplification

# Один файл
python stl_screenshot.py model.stl

# Пакет із вибраними ракурсами
python stl_screenshot.py "*.stl" --angles iso,front,top -o screenshots/ --tight-crop

# OpenSCAD із кольоровою схемою
python stl_screenshot.py model.stl --engine openscad --color-scheme Sunset

# Висока роздільність
python stl_screenshot.py model.stl --width 3840 --height 2160 --color '#ff6633'
```

## 📋 Параметри CLI

| Прапор | Default | Опис |
|---|---|---|
| `--engine` | `trimesh` | `trimesh` або `openscad` |
| `--angles` | `iso` | Ракурси через кому |
| `-o` / `--output` | поруч з файлом | Вихідний файл або тека |
| `--width`, `--height` | `1920`, `1080` | Роздільність |
| `--color` | `#3388cc` | Колір моделі (hex) для trimesh |
| `--bg-color` | `white` | Колір фону для trimesh |
| `--tight-crop` | off | Тісне кадрування |
| `--simplify` | `100000` | Макс. полігонів (0 = без спрощення) |
| `--color-scheme` | `Metallic` | Схема OpenSCAD |
| `-v` | off | Детальний вивід |

## 🏗 Збірка .exe

```bash
pip install pyinstaller customtkinter
python build_exe.py
```

Готовий .exe буде в `dist/STL Screenshot.exe`.

## 📂 Структура проекту

```
Stl To Img/
├── stl_screenshot.py       # CLI-скрипт рендерингу
├── stl_screenshot_gui.py   # GUI-програма
├── build_exe.py            # Скрипт збірки .exe
├── STL Screenshot.exe      # Готовий .exe
├── README.md
└── .gitignore
```

## 📦 Залежності

- Python 3.10+
- `trimesh` — завантаження STL
- `matplotlib` — рендеринг
- `numpy` — обчислення
- `Pillow` — зображення
- `fast-simplification` — спрощення сітки
- `customtkinter` — GUI
- `pyinstaller` — збірка .exe (лише для білду)

## 📄 Ліцензія

MIT
