#!/usr/bin/env python3
"""Скрипт збірки STL Screenshot у самодостатній .exe через PyInstaller."""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
GUI_SCRIPT = PROJECT_ROOT / "stl_screenshot_gui.py"
RENDER_SCRIPT = PROJECT_ROOT / "stl_screenshot.py"
NAME = "STL Screenshot"


def check_deps():
    """Перевіряємо чи встановлені необхідні пакети."""
    required = {
        "trimesh": "trimesh",
        "matplotlib": "matplotlib",
        "numpy": "numpy",
        "PIL": "Pillow",
        "customtkinter": "customtkinter",
        "PyInstaller": "pyinstaller",
    }
    missing = []
    for mod, pkg in required.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("❌ Бракує залежностей:")
        print(f"   pip install {' '.join(missing)}")
        sys.exit(1)
    print("✅ Всі залежності на місці")


def clean():
    """Видаляємо старі артефакти збірки."""
    for pattern in ["dist", "build", f"{NAME}.spec"]:
        for p in PROJECT_ROOT.glob(pattern):
            if p.is_dir():
                import shutil
                shutil.rmtree(p)
            else:
                p.unlink()
    print("🧹 Очищено")


def build():
    """Запускаємо PyInstaller."""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", NAME,
        "--add-data", f"{RENDER_SCRIPT.name};.",
        "--hidden-import", "mpl_toolkits.mplot3d.art3d",
        "--hidden-import", "matplotlib",
        "--hidden-import", "matplotlib.backends.backend_agg",
        "--hidden-import", "trimesh",
        "--clean",
        str(GUI_SCRIPT),
    ]

    print(f"▶ Збираємо {NAME}...")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    
    if result.returncode == 0:
        exe = PROJECT_ROOT / "dist" / f"{NAME}.exe"
        size_mb = exe.stat().st_size / (1024 * 1024)
        print(f"✅ Збірка завершена: {exe} ({size_mb:.0f} MB)")
    else:
        print(f"❌ Помилка збірки (код {result.returncode})")
        sys.exit(1)


if __name__ == "__main__":
    clean()
    check_deps()
    build()
