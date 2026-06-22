#!/usr/bin/env python3
"""
STL Screenshot Tool — автоматизований скріншот з STL файлів 3D моделей.

Використання:
  python stl_screenshot.py model.stl                          # один файл, 4 ракурси
  python stl_screenshot.py model.stl -o out.png                # один файл, один ракурс
  python stl_screenshot.py *.stl -o screenshots/               # пачка файлів
  python stl_screenshot.py *.stl --angles front,top,iso        # вибрані ракурси
  python stl_screenshot.py model.stl --engine openscad         # через OpenSCAD

Залежності: trimesh, matplotlib, numpy, Pillow
  pip install trimesh matplotlib numpy Pillow
"""

import argparse
import os
import sys
import math
import tempfile
import subprocess
from pathlib import Path

# ─── optional deps ────────────────────────────────────────────────

def _import_deps():
    """Import optional dependencies, return module handles or None."""
    deps = {}
    try:
        import trimesh
        deps['trimesh'] = trimesh
    except ImportError:
        deps['trimesh'] = None
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        deps['plt'] = plt
        deps['Poly3DCollection'] = Poly3DCollection
    except ImportError:
        deps['plt'] = None
    return deps

# ─── view angles ──────────────────────────────────────────────────

ANGLES = {
    'front':  dict(elev=0,   azim=0),      # спереду
    'back':   dict(elev=0,   azim=180),    # ззаду
    'left':   dict(elev=0,   azim=90),     # зліва
    'right':  dict(elev=0,   azim=-90),    # справа
    'top':    dict(elev=90,  azim=0),      # зверху
    'bottom': dict(elev=-90, azim=0),      # знизу
    'iso':    dict(elev=25,  azim=-45),    # ізометричний (default)
    'iso2':   dict(elev=25,  azim=135),    # ізометричний з іншого боку
}


# ─── render engines ───────────────────────────────────────────────

def render_trimesh(stl_path, output_path, elev=25, azim=-45,
                   width=1920, height=1080, dpi=150,
                   color='#3388cc', bg_color='white', edge_color=None,
                   mesh_simplify=None, tight_crop=False):
    """Render STL to PNG using trimesh + matplotlib."""
    deps = _import_deps()
    trimesh = deps['trimesh']
    plt = deps['plt']
    Poly3DCollection = deps['Poly3DCollection']
    
    if trimesh is None:
        raise ImportError("trimesh not installed. pip install trimesh")
    if plt is None:
        raise ImportError("matplotlib not installed. pip install matplotlib")
    
    # Load
    mesh = trimesh.load(stl_path)
    if isinstance(mesh, trimesh.Scene):
        meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
        if meshes:
            mesh = trimesh.util.concatenate(meshes)
        else:
            raise ValueError("No Trimesh objects found in scene")
    
    # Simplify if requested (for very large meshes)
    if mesh_simplify and len(mesh.faces) > mesh_simplify:
        print(f"  Simplifying mesh: {len(mesh.faces)} → {mesh_simplify} faces", file=sys.stderr)
        try:
            mesh = mesh.simplify_quadric_decimation(face_count=mesh_simplify)
        except (ImportError, Exception) as e:
            print(f"  Warning: simplification failed ({e}), rendering full mesh", file=sys.stderr)
    
    # Calculate figure size from dimensions and DPI
    figsize = (width / dpi, height / dpi)
    
    # Create figure
    fig = plt.figure(figsize=figsize, facecolor=bg_color)
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor(bg_color)
    
    # Get mesh vertices and faces
    vertices = mesh.vertices
    faces = mesh.faces
    
    from matplotlib.colors import to_rgba
    import numpy as np
    
    # --- Lighting: shade each face by its normal relative to light direction ---
    try:
        # Use trimesh face normals for accurate lighting
        face_normals = mesh.face_normals
        if face_normals is None or len(face_normals) == 0:
            raise ValueError("No normals")
    except Exception:
        # Compute face normals from vertices
        v = vertices[faces]
        edge1 = v[:, 1] - v[:, 0]
        edge2 = v[:, 2] - v[:, 0]
        face_normals = np.cross(edge1, edge2)
        norms = np.linalg.norm(face_normals, axis=1, keepdims=True)
        norms[norms == 0] = 1
        face_normals = face_normals / norms
    
    # Light direction — from upper-front-left (in view coordinates)
    # Rotate light with the view so it always comes from the same relative angle
    light_dir = np.array([-0.4, -0.3, 1.0])
    light_dir = light_dir / np.linalg.norm(light_dir)
    
    # Diffuse lighting: clamp dot product to [ambient, 1.0]
    cos_angles = np.dot(face_normals, light_dir)
    cos_angles = np.clip(cos_angles, 0.15, 1.0)
    
    # Build per-face colors with lighting
    base_rgb = np.array(to_rgba(color)[:3])
    face_colors = base_rgb * cos_angles[:, np.newaxis]
    face_colors = np.clip(face_colors, 0, 1)
    face_rgba = np.ones((len(face_colors), 4))
    face_rgba[:, :3] = face_colors
    face_rgba[:, 3] = 0.95  # alpha
    
    # Create poly collection with per-face colors
    mesh_collection = Poly3DCollection(vertices[faces])
    mesh_collection.set_facecolor(face_rgba)
    
    # Edges: thin darker lines for definition
    edge_rgb = np.clip(base_rgb * 0.45, 0, 1)
    mesh_collection.set_edgecolor(edge_rgb)
    mesh_collection.set_linewidth(0.08)
    
    ax.add_collection3d(mesh_collection)
    
    # Auto-scale
    bounds = mesh.bounds
    center = mesh.centroid
    extent = bounds[1] - bounds[0]
    
    if tight_crop:
        # Per-axis limits with 10% proportional padding
        padding = extent * 0.1
        xlo, xhi = bounds[0, 0] - padding[0], bounds[1, 0] + padding[0]
        ylo, yhi = bounds[0, 1] - padding[1], bounds[1, 1] + padding[1]
        zlo, zhi = bounds[0, 2] - padding[2], bounds[1, 2] + padding[2]
        ax.set_xlim(xlo, xhi)
        ax.set_ylim(ylo, yhi)
        ax.set_zlim(zlo, zhi)
        # Use proportional box aspect so nothing is stretched
        xr, yr, zr = xhi - xlo, yhi - ylo, zhi - zlo
        mr = max(xr, yr, zr)
        ax.set_box_aspect([xr/mr, yr/mr, zr/mr])
    else:
        # Square crop: equal padding based on max extent
        max_extent = extent.max()
        padding = max_extent * 0.15
        ax.set_xlim(center[0] - max_extent/2 - padding, center[0] + max_extent/2 + padding)
        ax.set_ylim(center[1] - max_extent/2 - padding, center[1] + max_extent/2 + padding)
        ax.set_zlim(center[2] - max_extent/2 - padding, center[2] + max_extent/2 + padding)
        ax.set_box_aspect([1, 1, 1])
    
    # Remove axes and set view
    ax.axis('off')
    ax.view_init(elev=elev, azim=azim)
    
    # Render
    plt.tight_layout(pad=0)
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight', 
                pad_inches=0, facecolor=bg_color)
    plt.close()
    
    return os.path.getsize(output_path)


def _find_openscad():
    """Locate OpenSCAD executable."""
    candidates = [
        r'C:\Program Files\OpenSCAD\openscad.com',
        r'C:\Program Files\OpenSCAD\openscad.exe',
        '/usr/bin/openscad',
        '/usr/local/bin/openscad',
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    import shutil
    return shutil.which('openscad') or shutil.which('openscad.com')


def render_openscad(stl_path, output_path, elev=25, azim=-45,
                    width=1920, height=1080,
                    color_scheme='Metallic', projection='p'):
    """Render STL to PNG using OpenSCAD CLI."""
    openscad = _find_openscad()
    if not openscad:
        raise RuntimeError("OpenSCAD not found. Install from https://openscad.org/")
    
    # Create temporary .scad file
    tmp_dir = tempfile.mkdtemp(prefix='stl_screenshot_')
    scad_path = os.path.join(tmp_dir, 'render.scad')
    
    # Convert STL path to absolute with forward slashes for OpenSCAD
    stl_abs = os.path.abspath(stl_path)
    stl_escaped = stl_abs.replace('\\', '/')
    
    with open(scad_path, 'w') as f:
        f.write(f'import("{stl_escaped}");\n')
    
    # Build command
    # OpenSCAD --camera: translate_x,y,z,rot_x,y,z,dist or eye_x,y,z,center_x,y,z
    # We use the first form: 0,0,0 (no translation), then rot_x (elev), rot_y (0), 
    # rot_z (azim), dist (auto with --viewall)
    # But --viewall and --camera don't work perfectly together.
    # Better: use --viewall + --autocenter alone for best fit, 
    # but then we can't control angles well.
    # Actually for angle control we need --camera with eye/center form
    # Let's use a reasonable distance based on model size estimation
    
    # Simpler approach: use --autocenter --viewall which auto-fits,
    # then camera rotation is handled by rotating the model itself
    # using rotate() in the SCAD file
    
    # SCAD approach: import + rotate for view control
    with open(scad_path, 'w') as f:
        f.write(f'rotate([{elev}, 0, {azim}])\n')
        f.write(f'  import("{stl_escaped}");\n')
    
    cmd = [
        openscad, '-q',
        '--autocenter',
        '--viewall',
        f'--imgsize={width},{height}',
        f'--projection={projection}',
        f'--colorscheme={color_scheme}',
        '-o', output_path,
        scad_path,
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    # Cleanup
    try:
        os.remove(scad_path)
        os.rmdir(tmp_dir)
    except OSError:
        pass
    
    if result.returncode != 0:
        raise RuntimeError(f"OpenSCAD failed: {result.stderr.strip()}")
    
    return os.path.getsize(output_path)


# ─── main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='STL Screenshot Tool — автоматизований скріншот STL моделей',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('files', nargs='+', help='STL файли для рендерингу')
    parser.add_argument('-o', '--output', default=None,
                        help='Вихідний файл або директорія (default: поряд з вхідним)')
    parser.add_argument('--engine', choices=['trimesh', 'openscad'], default='trimesh',
                        help='Рендер-рушій (default: trimesh)')
    parser.add_argument('--angles', default='iso',
                        help='Кути: front,back,left,right,top,bottom,iso,iso2 через кому')
    parser.add_argument('--width', type=int, default=1920, help='Ширина (default: 1920)')
    parser.add_argument('--height', type=int, default=1080, help='Висота (default: 1080)')
    parser.add_argument('--dpi', type=int, default=150, help='DPI trimesh (default: 150)')
    parser.add_argument('--color', default='#3388cc',
                        help='Колір моделі hex для trimesh (default: #3388cc)')
    parser.add_argument('--bg-color', default='white',
                        help='Колір фону для trimesh (default: white)')
    parser.add_argument('--color-scheme', default='Metallic',
                        help='Колірна схема OpenSCAD')
    parser.add_argument('--projection', choices=['o', 'p'], default='p',
                        help='Проєкція OpenSCAD: o=ortho, p=perspective')
    parser.add_argument('--simplify', type=int, default=100000,
                        help='Макс. полігонів для trimesh (0=без спрощення, default: 100000)')
    parser.add_argument('--tight-crop', action='store_true',
                        help='Тісне кадрування (менше порожнього простору)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Детальний вивід')
    
    args = parser.parse_args()
    
    # Parse angles
    angle_keys = [a.strip() for a in args.angles.split(',')]
    angle_list = []
    for key in angle_keys:
        if key in ANGLES:
            angle_list.append((key, ANGLES[key]))
        else:
            print(f"Попередження: невідомий кут '{key}'", file=sys.stderr)
    
    if not angle_list:
        print("Помилка: жодного валідного кута", file=sys.stderr)
        sys.exit(1)
    
    # Collect files
    import glob
    stl_files = []
    for pattern in args.files:
        matched = sorted(glob.glob(pattern, recursive=False))
        stl_files.extend(matched if matched else [pattern])
    stl_files = [f for f in stl_files if os.path.isfile(f)]
    
    if not stl_files:
        print("Помилка: не знайдено STL файлів", file=sys.stderr)
        sys.exit(1)
    
    print(f"STL файлів: {len(stl_files)}, ракурсів: {len(angle_list)}")
    print(f"Рушій: {args.engine}")
    if args.tight_crop:
        print("Кадрування: тісне")
    print()
    
    total = len(stl_files) * len(angle_list)
    count = 0
    errors = []
    
    for stl_path in stl_files:
        base = Path(stl_path).stem
        
        for angle_name, angle_params in angle_list:
            count += 1
            
            # Output path
            if args.output is None:
                out_path = str(Path(stl_path).parent / f"{base}_{angle_name}.png")
            elif os.path.isdir(args.output):
                dst = Path(args.output)
                dst.mkdir(parents=True, exist_ok=True)
                out_path = str(dst / f"{base}_{angle_name}.png")
            else:
                if len(stl_files) > 1 or len(angle_list) > 1:
                    p = Path(args.output)
                    out_path = str(p.parent / f"{p.stem}_{angle_name}{p.suffix or '.png'}")
                else:
                    out_path = args.output
            
            print(f"[{count}/{total}] {Path(stl_path).name} → {angle_name}...", end=' ', flush=True)
            
            try:
                if args.engine == 'trimesh':
                    render_trimesh(
                        stl_path, out_path,
                        elev=angle_params['elev'],
                        azim=angle_params['azim'],
                        width=args.width, height=args.height,
                        dpi=args.dpi, color=args.color,
                        bg_color=args.bg_color,
                        mesh_simplify=args.simplify if args.simplify > 0 else None,
                        tight_crop=args.tight_crop,
                    )
                else:
                    render_openscad(
                        stl_path, out_path,
                        elev=angle_params['elev'],
                        azim=angle_params['azim'],
                        width=args.width, height=args.height,
                        color_scheme=args.color_scheme,
                        projection=args.projection,
                    )
                
                size_kb = os.path.getsize(out_path) / 1024
                print(f"✓ ({size_kb:.0f} KB)")
                
            except Exception as e:
                print(f"✗ {e}")
                errors.append((stl_path, angle_name, str(e)))
    
    success = total - len(errors)
    print(f"\nГотово: {success}/{total} успішно")
    if errors:
        print(f"Помилок: {len(errors)}")
        for f, a, e in errors:
            print(f"  • {Path(f).name} [{a}]: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
