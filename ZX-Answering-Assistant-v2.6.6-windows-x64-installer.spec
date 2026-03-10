# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('src_compiled', 'src'), ('playwright_browsers', 'playwright_browsers'), ('flet_browsers/unpacked', 'flet_browsers/unpacked'), ('version.py', '.')]
binaries = []
hiddenimports = ['playwright', 'playwright.sync_api', 'playwright._impl._api_types', 'playwright._impl._browser', 'playwright._impl._connection', 'playwright._impl._helper', 'playwright._impl._page', 'playwright._impl._element_handle', 'playwright._impl._js_handle', 'greenlet', 'keyboard', 'requests', 'flet']
tmp_ret = collect_all('playwright')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'openpyxl', 'loguru', 'aiohttp', 'tqdm', 'scipy', 'yaml', 'dotenv', 'pyyaml'],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
    exclude_binaries=True,
    name='ZX-Answering-Assistant-v2.6.6-windows-x64-installer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZX-Answering-Assistant-v2.6.6-windows-x64-installer',
)
