# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for TS Diagnostic Tool.

Build with:
    pyinstaller --noconfirm packaging/ts_diag.spec

Output:
    dist/TSDiag/   <-- folder ready to be packaged by Inno Setup
"""
from pathlib import Path

# Resolve the project root from the .spec location. PyInstaller injects
# `SPECPATH` automatically; we use it so the build works no matter where
# you invoke `pyinstaller` from.
PROJECT_ROOT = Path(SPECPATH).parent.resolve()

block_cipher = None

# Hidden imports — paramiko and cantools both lazy-load submodules that
# PyInstaller doesn't always pick up by static analysis.
hiddenimports = [
    "paramiko",
    "paramiko.agent",
    "paramiko.transport",
    "paramiko.client",
    "cantools",
    "cantools.database",
    "cantools.database.can",
    "cantools.database.can.database",
    "cantools.database.can.message",
    "cryptography",
    "cryptography.hazmat",
    "cryptography.hazmat.backends",
    "cryptography.hazmat.backends.openssl",
    "PyQt6.sip",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
]

# We don't bundle the DBC or errq sources — those are read at runtime from
# the user's local repo (C:\__REPOS\ree-reecu_main by default). Keeping the
# installer small and avoiding stale copies of customer code.
datas = []

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim things we definitely don't use.
        "tkinter",
        "matplotlib",
        "PyQt5",
        "PySide2",
        "PySide6",
        "numpy.tests",
        "scipy",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ICON: optional. Drop a .ico into packaging/ and reference it here.
icon_path = PROJECT_ROOT / "packaging" / "ts_diag.ico"
icon_arg = str(icon_path) if icon_path.exists() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TSDiag",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # windowed app — no console pop-up
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="TSDiag",
)
