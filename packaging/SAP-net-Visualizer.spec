# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# パス設定（本specファイルのあるディレクトリを基準にルートを特定）
spec_dir = os.path.abspath(SPECPATH)
project_root = os.path.abspath(os.path.join(spec_dir, '..')) if os.path.basename(spec_dir) == 'packaging' else spec_dir
main_script = os.path.join(project_root, 'main.py')
icon_path = os.path.join(project_root, 'packaging', 'app_icon.ico')
version_file = os.environ.get('SAP_VERSION_INFO_PATH') or os.path.join(project_root, 'packaging', 'version_info.txt')

datas = []
binaries = []
hiddenimports = []

# Pygame のアセット・DLLを収集（不要なテスト・ドキュメント・サンプルを除外して軽量化・競合防止）
tmp_ret = collect_all('pygame')
datas += [d for d in tmp_ret[0] if not any(part in ['tests', 'docs', 'examples'] for part in d[0].replace('/', '\\').split('\\'))]
binaries += tmp_ret[1]
hiddenimports += [h for h in tmp_ret[2] if not (h.startswith('pygame.tests') or h.startswith('pygame.examples') or h.startswith('pygame.docs'))]
hiddenimports += ['yaml']

a = Analysis(
    [main_script],
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'pandas',
        'scipy',
        'PIL',
        'torch',
        'gymnasium',
        'tensorboard',
        'tkinter.test',
        'unittest',
        'pydoc',
        'doctest',
        'test',
        'pytest',
        'pygame.tests',
        'pygame.examples',
        'pygame.docs',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SAP-net-Visualizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
    version=version_file if os.path.exists(version_file) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SAP-net-Visualizer',
)
