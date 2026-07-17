# -*- mode: python ; coding: utf-8 -*-

import shutil


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='SmartVocabulary',
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
    icon=['assets\\icons8-Vocabulary-100.png'],
)

# Keep the editable prompt outside the one-file executable. This places it next
# to SmartVocabulary.exe without adding it to the PyInstaller data archive.
shutil.copy2(
    os.path.join(SPECPATH, 'gemini_prompt.txt'),
    os.path.join(DISTPATH, 'gemini_prompt.txt'),
)
