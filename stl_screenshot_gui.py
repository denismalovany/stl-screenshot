#!/usr/bin/env python3
"""
STL Screenshot GUI — програма для пакетного рендерингу STL файлів у PNG скріншоти.
"""

import sys
import os
import threading
import queue
from pathlib import Path

# ─── CustomTkinter ──────────────────────────────────────────────
import customtkinter as ctk
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Render engine import ───────────────────────────────────────
import numpy as np  # needed early for bundled mode

# Force these imports so PyInstaller picks them up
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: F401
import matplotlib  # noqa: F401

def _find_render_script():
    """Locate stl_screenshot.py in various bundle/runtime locations."""
    # PyInstaller bundled data
    if hasattr(sys, '_MEIPASS'):
        candidate = Path(sys._MEIPASS) / "stl_screenshot.py"
        if candidate.exists():
            return candidate
    # Next to this script
    candidate = Path(__file__).parent / "stl_screenshot.py"
    if candidate.exists():
        return candidate
    # Home directory
    candidate = Path.home() / "stl_screenshot.py"
    if candidate.exists():
        return candidate
    # Current directory
    candidate = Path.cwd() / "stl_screenshot.py"
    return candidate

RENDER_SCRIPT = _find_render_script()

# ─── Import render functions from stl_screenshot ─────────────────
_render_trimesh = None
_render_openscad = None
_ANGLES_DICT = {}

def _load_render_functions():
    """Load render functions from the script module (handles bundled .exe)."""
    global _render_trimesh, _render_openscad, _ANGLES_DICT
    
    import importlib.util
    if not RENDER_SCRIPT.exists():
        raise FileNotFoundError(f"stl_screenshot.py не знайдено за шляхом: {RENDER_SCRIPT}")
    
    # In bundled mode, add MEIPASS to sys.path so the import finds bundled deps
    if hasattr(sys, '_MEIPASS') and str(sys._MEIPASS) not in sys.path:
        sys.path.insert(0, str(sys._MEIPASS))
    
    spec = importlib.util.spec_from_file_location("stl_render", str(RENDER_SCRIPT))
    module = importlib.util.module_from_spec(spec)
    sys.modules['stl_render'] = module  # register to avoid re-imports
    spec.loader.exec_module(module)
    
    _render_trimesh = module.render_trimesh
    _render_openscad = module.render_openscad
    _ANGLES_DICT = module.ANGLES if hasattr(module, 'ANGLES') else {}

_load_render_functions()

ANGLES = ['iso', 'front', 'back', 'left', 'right', 'top', 'bottom', 'iso2']
COLOR_PRESETS = [
    ("#3399FF", "Синій"),
    ("#00CC66", "Зелений"),
    ("#FF6633", "Помаранчевий"),
    ("#CC3333", "Червоний"),
    ("#9933CC", "Фіолетовий"),
    ("#FFCC00", "Жовтий"),
    ("#66CCFF", "Блакитний"),
    ("#888888", "Сірий"),
]


class STLScreenshotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("STL Screenshot")
        self.geometry("800x720")
        self.minsize(680, 600)
        self.iconbitmap(default="")  # no icon for now

        # State
        self.stl_files = []
        self.output_dir = ""
        self.render_queue = queue.Queue()
        self.is_rendering = False

        # ─── Layout ──────────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # title
        self.grid_rowconfigure(1, weight=0)  # files frame
        self.grid_rowconfigure(2, weight=0)  # settings
        self.grid_rowconfigure(3, weight=0)  # output
        self.grid_rowconfigure(4, weight=1)  # log
        self.grid_rowconfigure(5, weight=0)  # buttons

        # ─── Title ───────────────────────────────────────────────
        title = ctk.CTkLabel(self, text="STL Screenshot", font=ctk.CTkFont(size=22, weight="bold"))
        title.grid(row=0, column=0, pady=(12, 4), padx=16, sticky="w")

        # ─── Files frame ─────────────────────────────────────────
        files_frame = ctk.CTkFrame(self)
        files_frame.grid(row=1, column=0, padx=16, pady=(4, 8), sticky="ew")
        files_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(files_frame, text="📁 STL файли:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=(12, 8), pady=10, sticky="w")

        self.files_label = ctk.CTkLabel(files_frame, text="Файлів не вибрано", text_color="gray")
        self.files_label.grid(row=0, column=1, padx=4, pady=10, sticky="w")

        btn_frame = ctk.CTkFrame(files_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=(4, 12), pady=10, sticky="e")

        self.add_btn = ctk.CTkButton(btn_frame, text="+ Додати файли", width=120, command=self.add_files)
        self.add_btn.pack(side="left", padx=2)

        self.clear_btn = ctk.CTkButton(btn_frame, text="✕ Очистити", width=90, fg_color="#555", command=self.clear_files)
        self.clear_btn.pack(side="left", padx=2)

        # ─── Settings frame ──────────────────────────────────────
        settings_frame = ctk.CTkFrame(self)
        settings_frame.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="ew")
        settings_frame.grid_columnconfigure(0, weight=1)
        settings_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(settings_frame, text="⚙ Налаштування", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=12, pady=(8, 2), sticky="w")

        # Column 0 — angles
        angles_box = ctk.CTkFrame(settings_frame, fg_color="transparent")
        angles_box.grid(row=1, column=0, padx=(12, 4), pady=(2, 8), sticky="nw")

        ctk.CTkLabel(angles_box, text="Ракурси:", font=ctk.CTkFont(size=12)).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))

        self.angle_vars = {}
        row, col = 1, 0
        for i, angle in enumerate(ANGLES):
            var = ctk.BooleanVar(value=(angle == 'iso'))
            self.angle_vars[angle] = var
            cb = ctk.CTkCheckBox(angles_box, text=angle, variable=var, width=70, checkbox_width=18, checkbox_height=18, font=ctk.CTkFont(size=12))
            cb.grid(row=row, column=col, padx=(0, 6), pady=1, sticky="w")
            col += 1
            if col >= 4:
                col = 0
                row += 1

        # Column 1 — other settings
        right_box = ctk.CTkFrame(settings_frame, fg_color="transparent")
        right_box.grid(row=1, column=1, padx=(4, 12), pady=(2, 8), sticky="nw")

        # Engine
        eng_row = ctk.CTkFrame(right_box, fg_color="transparent")
        eng_row.pack(fill="x", pady=1)
        ctk.CTkLabel(eng_row, text="Рушій:", width=70).pack(side="left")
        self.engine_var = ctk.StringVar(value="trimesh")
        engine_menu = ctk.CTkOptionMenu(eng_row, values=["trimesh", "openscad"], variable=self.engine_var, width=100)
        engine_menu.pack(side="left", padx=4)

        # Color
        color_row = ctk.CTkFrame(right_box, fg_color="transparent")
        color_row.pack(fill="x", pady=1)
        ctk.CTkLabel(color_row, text="Колір:", width=70).pack(side="left")
        self.color_var = ctk.StringVar(value="#3399FF")
        self.color_entry = ctk.CTkEntry(color_row, textvariable=self.color_var, width=90)
        self.color_entry.pack(side="left", padx=4)
        self.pick_color_btn = ctk.CTkButton(color_row, text="🎨", width=32, command=self.pick_color)
        self.pick_color_btn.pack(side="left", padx=2)

        # Resolution
        res_row = ctk.CTkFrame(right_box, fg_color="transparent")
        res_row.pack(fill="x", pady=1)
        ctk.CTkLabel(res_row, text="Роздільність:", width=70).pack(side="left")
        self.width_var = ctk.StringVar(value="1920")
        self.height_var = ctk.StringVar(value="1080")
        w_entry = ctk.CTkEntry(res_row, textvariable=self.width_var, width=60)
        w_entry.pack(side="left", padx=2)
        ctk.CTkLabel(res_row, text="×").pack(side="left")
        h_entry = ctk.CTkEntry(res_row, textvariable=self.height_var, width=60)
        h_entry.pack(side="left", padx=2)

        # Tight crop + Simplify
        extra_row = ctk.CTkFrame(right_box, fg_color="transparent")
        extra_row.pack(fill="x", pady=1)
        self.tight_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(extra_row, text="Тісне кадрування", variable=self.tight_var).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(extra_row, text="Simplify:").pack(side="left")
        self.simplify_var = ctk.StringVar(value="50000")
        simplify_entry = ctk.CTkEntry(extra_row, textvariable=self.simplify_var, width=70)
        simplify_entry.pack(side="left", padx=4)

        # ─── Output folder ──────────────────────────────────────
        out_frame = ctk.CTkFrame(self)
        out_frame.grid(row=3, column=0, padx=16, pady=(0, 8), sticky="ew")
        out_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(out_frame, text="💾 Зберегти в:", font=ctk.CTkFont(size=14)).grid(row=0, column=0, padx=(12, 8), pady=10, sticky="w")

        self.out_label = ctk.CTkLabel(out_frame, text="(не вибрано)", text_color="gray")
        self.out_label.grid(row=0, column=1, padx=4, pady=10, sticky="w")

        browse_btn = ctk.CTkButton(out_frame, text="📂 Огляд…", width=100, command=self.browse_output)
        browse_btn.grid(row=0, column=2, padx=(4, 12), pady=10, sticky="e")

        # ─── Log area ───────────────────────────────────────────
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=4, column=0, padx=16, pady=(0, 8), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(size=12, family="Consolas"), state="disabled")
        self.log_text.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")

        # ─── Bottom buttons ─────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=5, column=0, padx=16, pady=(0, 12), sticky="ew")

        self.open_out_btn = ctk.CTkButton(bottom, text="📂 Відкрити теку", fg_color="#555", command=self.open_output, state="disabled")
        self.open_out_btn.pack(side="left", padx=2)

        self.render_btn = ctk.CTkButton(bottom, text="▶ Рендерити", fg_color="#2a8", width=160, height=36,
                                        font=ctk.CTkFont(size=15, weight="bold"), command=self.start_render)
        self.render_btn.pack(side="right", padx=2)

        self.progress = ctk.CTkProgressBar(bottom, width=200)
        self.progress.pack(side="right", padx=(0, 12))
        self.progress.set(0)

        # ─── Bind keyboard ──────────────────────────────────────
        self.bind("<Control-o>", lambda e: self.add_files())
        self.bind("<Control-r>", lambda e: self.start_render())

        self.log("STL Screenshot GUI запущено")
        self.log("Додайте STL файли, виберіть теку та натисніть Рендерити")

    # ─── File operations ─────────────────────────────────────────

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Виберіть STL файли",
            filetypes=[("STL файли", "*.stl"), ("Всі файли", "*.*")]
        )
        if not files:
            return
        for f in files:
            if f not in self.stl_files:
                self.stl_files.append(f)
        self.update_files_label()

    def clear_files(self):
        self.stl_files.clear()
        self.update_files_label()

    def update_files_label(self):
        n = len(self.stl_files)
        if n == 0:
            self.files_label.configure(text="Файлів не вибрано", text_color="gray")
        else:
            total_mb = sum(os.path.getsize(f) for f in self.stl_files) / (1024 * 1024)
            self.files_label.configure(text=f"{n} файлів ({total_mb:.1f} MB)", text_color="white")

    # ─── Output ──────────────────────────────────────────────────

    def browse_output(self):
        d = filedialog.askdirectory(title="Виберіть теку для збереження")
        if d:
            self.output_dir = d
            self.out_label.configure(text=d, text_color="white")
            self.open_out_btn.configure(state="normal")

    def open_output(self):
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)

    # ─── Color picker ────────────────────────────────────────────

    def pick_color(self):
        # Simple preset picker
        top = ctk.CTkToplevel(self)
        top.title("Виберіть колір")
        top.geometry("420x140")
        top.transient(self)
        top.grab_set()

        ctk.CTkLabel(top, text="Оберіть колір моделі:").pack(pady=(10, 6))

        frame = ctk.CTkFrame(top, fg_color="transparent")
        frame.pack(pady=4)

        row, col = 0, 0
        for hex_val, name in COLOR_PRESETS:
            btn = ctk.CTkButton(frame, text="", width=36, height=36, fg_color=hex_val, hover_color=hex_val,
                                corner_radius=18)
            btn.configure(command=lambda h=hex_val: self.set_color(h, top))
            btn.grid(row=row, column=col, padx=4, pady=4)
            col += 1
            if col >= 8:
                col = 0
                row += 1

    def set_color(self, hex_val, window):
        self.color_var.set(hex_val)
        window.destroy()

    # ─── Rendering ───────────────────────────────────────────────

    def log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.update()

    def start_render(self):
        if self.is_rendering:
            return
        if not self.stl_files:
            messagebox.showwarning("Немає файлів", "Додайте хоча б один STL файл")
            return
        if not self.output_dir:
            messagebox.showwarning("Немає теки", "Виберіть теку для збереження")
            return

        # Validate angles
        selected_angles = [a for a in ANGLES if self.angle_vars[a].get()]
        if not selected_angles:
            messagebox.showwarning("Немає ракурсів", "Виберіть хоча б один ракурс")
            return

        self.is_rendering = True
        self.render_btn.configure(text="⏳ Рендеринг...", state="disabled")
        self.progress.set(0)

        # Gather render params
        params = {
            'files': self.stl_files,
            'angles': selected_angles,
            'output_dir': self.output_dir,
            'engine': self.engine_var.get(),
            'color': self.color_var.get(),
            'width': int(self.width_var.get() or 1920),
            'height': int(self.height_var.get() or 1080),
            'tight_crop': self.tight_var.get(),
            'simplify': int(self.simplify_var.get()) if self.simplify_var.get().strip() else 100000,
        }

        total = len(params['files']) * len(params['angles'])
        self.log(f"▶ Запуск рендерингу: {len(params['files'])} файлів × {len(params['angles'])} ракурсів = {total} знімків")
        self.log(f"   Рушій: {params['engine']}, колір: {params['color']}")
        self.log(f"   Тека: {params['output_dir']}")
        self.log("")

        # Run in thread
        thread = threading.Thread(target=self._render_thread, args=(params, total), daemon=True)
        thread.start()
        self.after(100, self._poll_thread)

    def _render_thread(self, params, total):
        try:
            files = params['files']
            angles = params['angles']
            out_dir = params['output_dir']
            engine = params['engine']

            done_count = 0
            errors = []

            for stl_path in files:
                base = Path(stl_path).stem
                for angle_name in angles:
                    done_count += 1
                    angle_params = _ANGLES_DICT.get(angle_name, {'elev': 25, 'azim': -45})

                    # Output path
                    out_path = str(Path(out_dir) / f"{base}_{angle_name}.png")

                    self.render_queue.put(("log", f"[{done_count}/{total}] {Path(stl_path).name} → {angle_name}..."))
                    self.render_queue.put(("progress", (done_count - 1) / total))

                    try:
                        if engine == 'trimesh':
                            _render_trimesh(
                                stl_path, out_path,
                                elev=angle_params['elev'],
                                azim=angle_params['azim'],
                                width=params['width'],
                                height=params['height'],
                                color=params['color'],
                                mesh_simplify=params['simplify'] if params['simplify'] > 0 else None,
                                tight_crop=params['tight_crop'],
                            )
                        else:
                            _render_openscad(
                                stl_path, out_path,
                                elev=angle_params['elev'],
                                azim=angle_params['azim'],
                                width=params['width'],
                                height=params['height'],
                            )

                        size_kb = os.path.getsize(out_path) / 1024
                        self.render_queue.put(("log", f"   ✓ {out_path} ({size_kb:.0f} KB)"))

                    except Exception as e:
                        self.render_queue.put(("log", f"   ✗ ПОМИЛКА: {e}"))
                        errors.append((Path(stl_path).name, angle_name, str(e)))

                    self.render_queue.put(("progress", done_count / total))

            if errors:
                self.render_queue.put(("log", ""))
                self.render_queue.put(("log", f"❌ {len(errors)} помилок:"))
                for f, a, e in errors:
                    self.render_queue.put(("log", f"   • {f} [{a}]: {e}"))
                self.render_queue.put(("status", f"⚠ Рендеринг завершено з {len(errors)} помилками (успішно: {total - len(errors)}/{total})"))
            else:
                self.render_queue.put(("status", f"✅ Рендеринг завершено! {total} знімків успішно"))

        except Exception as e:
            self.render_queue.put(("log", f"ПОМИЛКА: {e}"))
            self.render_queue.put(("status", f"❌ Критична помилка: {e}"))

        self.render_queue.put(("done", None))

    def _poll_thread(self):
        try:
            while True:
                msg_type, data = self.render_queue.get_nowait()
                if msg_type == "log":
                    self.log(data)
                elif msg_type == "progress":
                    self.progress.set(data)
                elif msg_type == "status":
                    self.log("")
                    self.log(data)
                elif msg_type == "done":
                    self.is_rendering = False
                    self.render_btn.configure(text="▶ Рендерити", state="normal")
                    self.progress.set(1.0)
                    self.open_out_btn.configure(state="normal")
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_thread)


# ─── Entry point ─────────────────────────────────────────────────

if __name__ == "__main__":
    app = STLScreenshotGUI()
    app.mainloop()
