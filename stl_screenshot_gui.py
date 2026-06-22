#!/usr/bin/env python3
"""
STL Screenshot GUI — batch STL to PNG renderer with diffuse lighting.
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

# ─── Translations ────────────────────────────────────────────────

T = {
    'en': {
        'title': "STL Screenshot",
        'files_header': "📁 STL files:",
        'files_none': "No files selected",
        'add_files': "+ Add files",
        'clear_files': "✕ Clear",
        'settings': "⚙ Settings",
        'angles_label': "Views:",
        'engine_label': "Engine:",
        'color_label': "Color:",
        'resolution_label': "Resolution:",
        'tight_crop': "Tight crop",
        'simplify_label': "Simplify:",
        'output_header': "💾 Save to:",
        'output_none': "(not selected)",
        'browse': "📂 Browse…",
        'open_folder': "📂 Open folder",
        'render': "▶ Render",
        'rendering': "⏳ Rendering...",
        'pick_color_title': "Pick a color",
        'pick_color_prompt': "Choose model color:",
        'startup_1': "STL Screenshot GUI started",
        'startup_2': "Add STL files, choose output folder, and click Render",
        'warning_no_files': "No files",
        'warning_no_files_msg': "Add at least one STL file",
        'warning_no_output': "No folder",
        'warning_no_output_msg': "Choose an output folder",
        'warning_no_angles': "No views",
        'warning_no_angles_msg': "Select at least one view angle",
        'render_start': "▶ Starting render: {n_files} files × {n_angles} views = {total} screenshots",
        'render_engine': "Engine: {engine}, color: {color}",
        'render_folder': "Folder: {output_dir}",
        'render_line': "[{done}/{total}] {name} → {angle}...",
        'render_ok': "   ✓ {path} ({size:.0f} KB)",
        'render_error': "   ✗ ERROR: {e}",
        'error_summary': "❌ {n} errors:",
        'error_item': "   • {f} [{a}]: {e}",
        'status_errors': "⚠ Render done with {n} errors (ok: {ok}/{total})",
        'status_ok': "✅ Render complete! {total} screenshots",
        'critical_error': "❌ Critical error: {e}",
        'file_dialog_title': "Select STL files",
        'file_dialog_stl': "STL files",
        'file_dialog_all': "All files",
        'folder_dialog_title': "Choose output folder",
        'color_names': ["Blue", "Green", "Orange", "Red", "Purple", "Yellow", "Light Blue", "Gray"],
    },
    'uk': {
        'title': "STL Screenshot",
        'files_header': "📁 STL файли:",
        'files_none': "Файлів не вибрано",
        'add_files': "+ Додати файли",
        'clear_files': "✕ Очистити",
        'settings': "⚙ Налаштування",
        'angles_label': "Ракурси:",
        'engine_label': "Рушій:",
        'color_label': "Колір:",
        'resolution_label': "Роздільність:",
        'tight_crop': "Тісне кадрування",
        'simplify_label': "Simplify:",
        'output_header': "💾 Зберегти в:",
        'output_none': "(не вибрано)",
        'browse': "📂 Огляд…",
        'open_folder': "📂 Відкрити теку",
        'render': "▶ Рендерити",
        'rendering': "⏳ Рендеринг...",
        'pick_color_title': "Виберіть колір",
        'pick_color_prompt': "Оберіть колір моделі:",
        'startup_1': "STL Screenshot GUI запущено",
        'startup_2': "Додайте STL файли, виберіть теку та натисніть Рендерити",
        'warning_no_files': "Немає файлів",
        'warning_no_files_msg': "Додайте хоча б один STL файл",
        'warning_no_output': "Немає теки",
        'warning_no_output_msg': "Виберіть теку для збереження",
        'warning_no_angles': "Немає ракурсів",
        'warning_no_angles_msg': "Виберіть хоча б один ракурс",
        'render_start': "▶ Запуск рендерингу: {n_files} файлів × {n_angles} ракурсів = {total} знімків",
        'render_engine': "Рушій: {engine}, колір: {color}",
        'render_folder': "Тека: {output_dir}",
        'render_line': "[{done}/{total}] {name} → {angle}...",
        'render_ok': "   ✓ {path} ({size:.0f} KB)",
        'render_error': "   ✗ ПОМИЛКА: {e}",
        'error_summary': "❌ {n} помилок:",
        'error_item': "   • {f} [{a}]: {e}",
        'status_errors': "⚠ Рендеринг завершено з {n} помилками (успішно: {ok}/{total})",
        'status_ok': "✅ Рендеринг завершено! {total} знімків",
        'critical_error': "❌ Критична помилка: {e}",
        'file_dialog_title': "Виберіть STL файли",
        'file_dialog_stl': "STL файли",
        'file_dialog_all': "Всі файли",
        'folder_dialog_title': "Виберіть теку для збереження",
        'color_names': ["Синій", "Зелений", "Помаранчевий", "Червоний", "Фіолетовий", "Жовтий", "Блакитний", "Сірий"],
    }
}

# ─── OpenSCAD detection ──────────────────────────────────────────
def _find_openscad():
    import shutil
    candidates = [
        r'C:\Program Files\OpenSCAD\openscad.com',
        r'C:\Program Files\OpenSCAD\openscad.exe',
        '/usr/bin/openscad',
        '/usr/local/bin/openscad',
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return shutil.which('openscad') or shutil.which('openscad.com')

OPENSCAD_PATH = _find_openscad()
HAS_OPENSCAD = OPENSCAD_PATH is not None

ENGINE_CHOICES = ["trimesh"]
if HAS_OPENSCAD:
    ENGINE_CHOICES.append("openscad")

# ─── Render engine import ───────────────────────────────────────
import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: F401
import matplotlib  # noqa: F401

def _find_render_script():
    if hasattr(sys, '_MEIPASS'):
        candidate = Path(sys._MEIPASS) / "stl_screenshot.py"
        if candidate.exists():
            return candidate
    candidate = Path(__file__).parent / "stl_screenshot.py"
    if candidate.exists():
        return candidate
    candidate = Path.home() / "stl_screenshot.py"
    if candidate.exists():
        return candidate
    return Path.cwd() / "stl_screenshot.py"

RENDER_SCRIPT = _find_render_script()

_render_trimesh = None
_render_openscad = None
_ANGLES_DICT = {}

def _load_render_functions():
    global _render_trimesh, _render_openscad, _ANGLES_DICT
    import importlib.util
    if not RENDER_SCRIPT.exists():
        raise FileNotFoundError(f"stl_screenshot.py not found: {RENDER_SCRIPT}")
    if hasattr(sys, '_MEIPASS') and str(sys._MEIPASS) not in sys.path:
        sys.path.insert(0, str(sys._MEIPASS))
    spec = importlib.util.spec_from_file_location("stl_render", str(RENDER_SCRIPT))
    module = importlib.util.module_from_spec(spec)
    sys.modules['stl_render'] = module
    spec.loader.exec_module(module)
    _render_trimesh = module.render_trimesh
    _render_openscad = module.render_openscad
    _ANGLES_DICT = module.ANGLES if hasattr(module, 'ANGLES') else {}

_load_render_functions()

ANGLES = ['iso', 'front', 'back', 'left', 'right', 'top', 'bottom', 'iso2']
COLOR_HEX = ["#3399FF", "#00CC66", "#FF6633", "#CC3333", "#9933CC", "#FFCC00", "#66CCFF", "#888888"]


class STLScreenshotGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.lang = 'uk'
        self.tr = lambda key: T[self.lang].get(key, key)

        self.title(self.tr('title'))
        self.geometry("800x720")
        self.minsize(680, 600)
        self.iconbitmap(default="")

        self.stl_files = []
        self.output_dir = ""
        self.render_queue = queue.Queue()
        self.is_rendering = False

        # Store widget references for i18n
        self._i18n_widgets = {}

        # ─── Layout ──────────────────────────────────────────────
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=0)
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(4, weight=1)
        self.grid_rowconfigure(5, weight=0)

        self._build_ui()
        self._apply_language()

        self.log(self.tr('startup_1'))
        self.log(self.tr('startup_2'))

    # ─── Translation helper ─────────────────────────────────────

    def _i18n(self, key):
        """Return translatable string for current language."""
        return T[self.lang].get(key, key)

    def _t(self, fmt, **kwargs):
        """Format a translatable template with kwargs."""
        return T[self.lang].get(fmt, fmt).format(**kwargs)

    def _register(self, key, widget, attr='text'):
        """Register a widget for language switching."""
        if key not in self._i18n_widgets:
            self._i18n_widgets[key] = []
        self._i18n_widgets[key].append((widget, attr))

    def _apply_language(self):
        """Update all registered widgets to current language."""
        for key, entries in self._i18n_widgets.items():
            translated = T[self.lang].get(key)
            if translated is None:
                continue
            for widget, attr in entries:
                try:
                    if attr == 'text':
                        widget.configure(text=translated)
                except Exception:
                    pass

        # Update files label (dynamic content)
        self.update_files_label()

        # Update output label
        if self.output_dir:
            self.out_label.configure(text=self.output_dir, text_color="white")
        else:
            self.out_label.configure(text=self._i18n('output_none'), text_color="gray")

        # Update color picker names
        self._color_names = T[self.lang].get('color_names', [])

    def toggle_language(self):
        """Switch between Ukrainian and English."""
        self.lang = 'en' if self.lang == 'uk' else 'uk'
        self._apply_language()
        self.lang_btn.configure(text="🇬🇧" if self.lang == 'uk' else "🇺🇦")

    # ─── UI Builder ─────────────────────────────────────────────

    def _build_ui(self):
        # Title row with language toggle
        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.grid(row=0, column=0, pady=(12, 4), padx=16, sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(title_row, text="STL Screenshot", font=ctk.CTkFont(size=22, weight="bold"))
        title_lbl.grid(row=0, column=0, sticky="w")
        self._register('title', title_lbl)

        self.lang_btn = ctk.CTkButton(title_row, text="🇬🇧" if self.lang == 'uk' else "🇺🇦",
                                      width=40, height=28, fg_color="#444",
                                      command=self.toggle_language)
        self.lang_btn.grid(row=0, column=1, sticky="e")

        # ─── Files frame
        files_frame = ctk.CTkFrame(self)
        files_frame.grid(row=1, column=0, padx=16, pady=(4, 8), sticky="ew")
        files_frame.grid_columnconfigure(1, weight=1)

        fl = ctk.CTkLabel(files_frame, font=ctk.CTkFont(size=14))
        fl.grid(row=0, column=0, padx=(12, 8), pady=10, sticky="w")
        self._register('files_header', fl)

        self.files_label = ctk.CTkLabel(files_frame, text_color="gray")
        self.files_label.grid(row=0, column=1, padx=4, pady=10, sticky="w")
        self._register('files_none', self.files_label)

        btn_frame = ctk.CTkFrame(files_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=2, padx=(4, 12), pady=10, sticky="e")

        self.add_btn = ctk.CTkButton(btn_frame, width=120, command=self.add_files)
        self.add_btn.pack(side="left", padx=2)
        self._register('add_files', self.add_btn)

        self.clear_btn = ctk.CTkButton(btn_frame, width=90, fg_color="#555", command=self.clear_files)
        self.clear_btn.pack(side="left", padx=2)
        self._register('clear_files', self.clear_btn)

        # ─── Settings frame
        settings_frame = ctk.CTkFrame(self)
        settings_frame.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="ew")
        settings_frame.grid_columnconfigure(0, weight=1)
        settings_frame.grid_columnconfigure(1, weight=1)

        sl = ctk.CTkLabel(settings_frame, font=ctk.CTkFont(size=14))
        sl.grid(row=0, column=0, padx=12, pady=(8, 2), sticky="w")
        self._register('settings', sl)

        # Column 0 — angles
        angles_box = ctk.CTkFrame(settings_frame, fg_color="transparent")
        angles_box.grid(row=1, column=0, padx=(12, 4), pady=(2, 8), sticky="nw")

        al = ctk.CTkLabel(angles_box, font=ctk.CTkFont(size=12))
        al.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 4))
        self._register('angles_label', al)

        self.angle_vars = {}
        r, c = 1, 0
        for angle in ANGLES:
            var = ctk.BooleanVar(value=(angle == 'iso'))
            self.angle_vars[angle] = var
            cb = ctk.CTkCheckBox(angles_box, text=angle, variable=var, width=70,
                                 checkbox_width=18, checkbox_height=18, font=ctk.CTkFont(size=12))
            cb.grid(row=r, column=c, padx=(0, 6), pady=1, sticky="w")
            c += 1
            if c >= 4:
                c = 0
                r += 1

        # Column 1 — other settings
        right_box = ctk.CTkFrame(settings_frame, fg_color="transparent")
        right_box.grid(row=1, column=1, padx=(4, 12), pady=(2, 8), sticky="nw")

        # Engine
        eng_row = ctk.CTkFrame(right_box, fg_color="transparent")
        eng_row.pack(fill="x", pady=1)
        el = ctk.CTkLabel(eng_row, width=70)
        el.pack(side="left")
        self._register('engine_label', el)

        self.engine_var = ctk.StringVar(value="trimesh")
        ctk.CTkOptionMenu(eng_row, values=ENGINE_CHOICES, variable=self.engine_var, width=100).pack(side="left", padx=4)

        # Color
        color_row = ctk.CTkFrame(right_box, fg_color="transparent")
        color_row.pack(fill="x", pady=1)
        cl = ctk.CTkLabel(color_row, width=70)
        cl.pack(side="left")
        self._register('color_label', cl)

        self.color_var = ctk.StringVar(value="#3399FF")
        self.color_entry = ctk.CTkEntry(color_row, textvariable=self.color_var, width=90)
        self.color_entry.pack(side="left", padx=4)
        self.pick_color_btn = ctk.CTkButton(color_row, text="🎨", width=32, command=self.pick_color)
        self.pick_color_btn.pack(side="left", padx=2)

        # Resolution
        res_row = ctk.CTkFrame(right_box, fg_color="transparent")
        res_row.pack(fill="x", pady=1)
        rl = ctk.CTkLabel(res_row, width=70)
        rl.pack(side="left")
        self._register('resolution_label', rl)

        self.width_var = ctk.StringVar(value="1920")
        self.height_var = ctk.StringVar(value="1080")
        ctk.CTkEntry(res_row, textvariable=self.width_var, width=60).pack(side="left", padx=2)
        ctk.CTkLabel(res_row, text="×").pack(side="left")
        ctk.CTkEntry(res_row, textvariable=self.height_var, width=60).pack(side="left", padx=2)

        # Tight crop + Simplify
        extra_row = ctk.CTkFrame(right_box, fg_color="transparent")
        extra_row.pack(fill="x", pady=1)
        self.tight_var = ctk.BooleanVar(value=True)
        tc = ctk.CTkCheckBox(extra_row, variable=self.tight_var)
        tc.pack(side="left", padx=(0, 12))
        self._register('tight_crop', tc)

        sl2 = ctk.CTkLabel(extra_row)
        sl2.pack(side="left")
        self._register('simplify_label', sl2)
        self.simplify_var = ctk.StringVar(value="50000")
        ctk.CTkEntry(extra_row, textvariable=self.simplify_var, width=70).pack(side="left", padx=4)

        # ─── Output folder
        out_frame = ctk.CTkFrame(self)
        out_frame.grid(row=3, column=0, padx=16, pady=(0, 8), sticky="ew")
        out_frame.grid_columnconfigure(1, weight=1)

        oh = ctk.CTkLabel(out_frame, font=ctk.CTkFont(size=14))
        oh.grid(row=0, column=0, padx=(12, 8), pady=10, sticky="w")
        self._register('output_header', oh)

        self.out_label = ctk.CTkLabel(out_frame, text_color="gray")
        self.out_label.grid(row=0, column=1, padx=4, pady=10, sticky="w")
        self._register('output_none', self.out_label)

        self.browse_btn = ctk.CTkButton(out_frame, width=100, command=self.browse_output)
        self.browse_btn.grid(row=0, column=2, padx=(4, 12), pady=10, sticky="e")
        self._register('browse', self.browse_btn)

        # ─── Log area
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=4, column=0, padx=16, pady=(0, 8), sticky="nsew")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(log_frame, font=ctk.CTkFont(size=12, family="Consolas"), state="disabled")
        self.log_text.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")

        # ─── Bottom buttons
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=5, column=0, padx=16, pady=(0, 12), sticky="ew")

        self.open_out_btn = ctk.CTkButton(bottom, fg_color="#555", command=self.open_output, state="disabled")
        self.open_out_btn.pack(side="left", padx=2)
        self._register('open_folder', self.open_out_btn)

        self.render_btn = ctk.CTkButton(bottom, fg_color="#2a8", width=160, height=36,
                                        font=ctk.CTkFont(size=15, weight="bold"), command=self.start_render)
        self.render_btn.pack(side="right", padx=2)
        self._register('render', self.render_btn)

        self.progress = ctk.CTkProgressBar(bottom, width=200)
        self.progress.pack(side="right", padx=(0, 12))
        self.progress.set(0)

        # ─── Keyboard
        self.bind("<Control-o>", lambda e: self.add_files())
        self.bind("<Control-r>", lambda e: self.start_render())

    # ─── File operations ─────────────────────────────────────────

    def add_files(self):
        tr = self._i18n
        files = filedialog.askopenfilenames(
            title=tr('file_dialog_title'),
            filetypes=[(tr('file_dialog_stl'), "*.stl"), (tr('file_dialog_all'), "*.*")]
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
            self.files_label.configure(text=self._i18n('files_none'), text_color="gray")
        else:
            total_mb = sum(os.path.getsize(f) for f in self.stl_files) / (1024 * 1024)
            self.files_label.configure(text=f"{n} files ({total_mb:.1f} MB)", text_color="white")

    # ─── Output ──────────────────────────────────────────────────

    def browse_output(self):
        d = filedialog.askdirectory(title=self._i18n('folder_dialog_title'))
        if d:
            self.output_dir = d
            self.out_label.configure(text=d, text_color="white")
            self.open_out_btn.configure(state="normal")

    def open_output(self):
        if self.output_dir and os.path.isdir(self.output_dir):
            os.startfile(self.output_dir)

    # ─── Color picker ────────────────────────────────────────────

    def pick_color(self):
        tr = self._i18n
        top = ctk.CTkToplevel(self)
        top.title(tr('pick_color_title'))
        top.geometry("420x140")
        top.transient(self)
        top.grab_set()

        ctk.CTkLabel(top, text=tr('pick_color_prompt')).pack(pady=(10, 6))

        frame = ctk.CTkFrame(top, fg_color="transparent")
        frame.pack(pady=4)

        names = T[self.lang].get('color_names', [str(i) for i in range(len(COLOR_HEX))])
        row, col = 0, 0
        for i, hex_val in enumerate(COLOR_HEX):
            name = names[i] if i < len(names) else hex_val
            btn = ctk.CTkButton(frame, text="", width=36, height=36, fg_color=hex_val,
                                hover_color=hex_val, corner_radius=18)
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
        tr = self._i18n
        if not self.stl_files:
            messagebox.showwarning(tr('warning_no_files'), tr('warning_no_files_msg'))
            return
        if not self.output_dir:
            messagebox.showwarning(tr('warning_no_output'), tr('warning_no_output_msg'))
            return

        selected_angles = [a for a in ANGLES if self.angle_vars[a].get()]
        if not selected_angles:
            messagebox.showwarning(tr('warning_no_angles'), tr('warning_no_angles_msg'))
            return

        self.is_rendering = True
        self.render_btn.configure(text=self._i18n('rendering'), state="disabled")
        self.progress.set(0)

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
        self.log(self._t('render_start', n_files=len(params['files']), n_angles=len(params['angles']), total=total))
        self.log(self._t('render_engine', engine=params['engine'], color=params['color']))
        self.log(self._t('render_folder', output_dir=params['output_dir']))
        self.log("")

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
                    out_path = str(Path(out_dir) / f"{base}_{angle_name}.png")

                    self.render_queue.put(("log",
                        self._t('render_line', done=done_count, total=total,
                                name=Path(stl_path).name, angle=angle_name)))
                    self.render_queue.put(("progress", (done_count - 1) / total))

                    try:
                        if engine == 'trimesh':
                            _render_trimesh(
                                stl_path, out_path,
                                elev=angle_params['elev'], azim=angle_params['azim'],
                                width=params['width'], height=params['height'],
                                color=params['color'],
                                mesh_simplify=params['simplify'] if params['simplify'] > 0 else None,
                                tight_crop=params['tight_crop'],
                            )
                        else:
                            _render_openscad(
                                stl_path, out_path,
                                elev=angle_params['elev'], azim=angle_params['azim'],
                                width=params['width'], height=params['height'],
                            )

                        size_kb = os.path.getsize(out_path) / 1024
                        self.render_queue.put(("log", self._t('render_ok', path=out_path, size=size_kb)))

                    except Exception as e:
                        self.render_queue.put(("log", self._t('render_error', e=e)))
                        errors.append((Path(stl_path).name, angle_name, str(e)))

                    self.render_queue.put(("progress", done_count / total))

            if errors:
                self.render_queue.put(("log", ""))
                self.render_queue.put(("log", self._t('error_summary', n=len(errors))))
                for f, a, e in errors:
                    self.render_queue.put(("log", self._t('error_item', f=f, a=a, e=e)))
                self.render_queue.put(("status", self._t('status_errors', n=len(errors), ok=total-len(errors), total=total)))
            else:
                self.render_queue.put(("status", self._t('status_ok', total=total)))

        except Exception as e:
            self.render_queue.put(("log", self._t('critical_error', e=e)))
            self.render_queue.put(("status", self._t('critical_error', e=e)))

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
                    self.render_btn.configure(text=self._i18n('render'), state="normal")
                    self.progress.set(1.0)
                    self.open_out_btn.configure(state="normal")
                    return
        except queue.Empty:
            pass
        self.after(100, self._poll_thread)


if __name__ == "__main__":
    app = STLScreenshotGUI()
    app.mainloop()
