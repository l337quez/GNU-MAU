# -*- mode: python ; coding: utf-8 -*-
import os

base_path = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(base_path, 'assets'), 'assets'),
    (os.path.join(base_path, 'themes'), 'themes'),
]

hiddenimports = [
    'PySide6.QtXml',
    'PySide6.QtOpenGL',
    'PySide6.QtSvg',
    'mongita',
    'markdown2',
    'dotenv',
    'gkeepapi',
    'qtpynodeeditor',
]

a = Analysis(
    ['main.py'],
    pathex=[base_path],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='gnu-mau',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app/mau.png',
)
