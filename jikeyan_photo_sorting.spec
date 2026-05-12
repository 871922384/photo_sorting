from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs


project_root = Path(SPECPATH).resolve()
app_icon_path = project_root / "packaging" / "windows" / "assets" / "jikeyan_app_icon.ico"
version_info_path = project_root / "packaging" / "windows" / "file_version_info.txt"
readme_path = project_root / "README.txt"

datas = [
    (str(app_icon_path), "branding"),
]
if readme_path.exists():
    datas.append((str(readme_path), "."))

binaries = collect_dynamic_libs("pyzbar")

a = Analysis(
    ["main.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=["numpy", "numpy.core", "numpy.fft", "numpy.lib", "pyzbar", "zxingcpp"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="jikeyan-photo-sorting",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    icon=str(app_icon_path),
    version=str(version_info_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="jikeyan-photo-sorting",
)
