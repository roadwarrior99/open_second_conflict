# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec file for Second Conflict.
#
# Usage (run from the project root):
#   pyinstaller build/second_conflict.spec
#
# Output lands in dist/Second Conflict/  (onedir mode).
# The build/ folder only contains PyInstaller's intermediate work files.

import sys
import os

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=['..'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # pygame sub-modules that PyInstaller misses on some platforms
        'pygame.mixer',
        'pygame.font',
        'pygame.image',
        'pygame.transform',
        'pygame.draw',
        'pygame.event',
        'pygame.time',
        'pygame.display',
        'pygame.rect',
        'pygame.surface',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'PIL',
        'email',
        'xml',
        'html',
        'http',
        'unittest',
        'pydoc',
        'doctest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ---- Platform-specific icon ------------------------------------------------
_here = os.path.dirname(os.path.abspath(SPEC))
_icon_win = os.path.join(_here, 'icon.ico')
_icon_mac = os.path.join(_here, 'icon.icns')

_icon = None
if sys.platform == 'win32' and os.path.isfile(_icon_win):
    _icon = _icon_win
elif sys.platform == 'darwin' and os.path.isfile(_icon_mac):
    _icon = _icon_mac
# ----------------------------------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Second Conflict',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,       # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Second Conflict',
)

# macOS: wrap in an .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='Second Conflict.app',
        icon=_icon_mac if (_icon_mac and os.path.isfile(_icon_mac)) else None,
        bundle_identifier='com.secondconflict.game',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.13',
            'NSHumanReadableCopyright': 'Second Conflict — Jerry W. Galloway (1991)',
        },
    )