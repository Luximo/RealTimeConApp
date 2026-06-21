# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, copy_metadata, collect_data_files

# Collect everything PyQt6 needs (plugins, binaries, Qt libs)
qt_datas, qt_binaries, qt_hiddenimports = collect_all('PyQt6')

# Perth and Chatterbox bundle model checkpoint files as package data
perth_datas = collect_data_files('perth')
chatterbox_datas = collect_data_files('chatterbox')

# Metadata for packages checked via pkg_resources at runtime
runtime_metadata = []
for pkg in [
    'requests', 'huggingface_hub', 'transformers', 'tokenizers',
    'filelock', 'packaging', 'tqdm', 'certifi', 'charset-normalizer',
    'urllib3', 'idna', 'pyyaml', 'regex', 'safetensors',
]:
    try:
        runtime_metadata += copy_metadata(pkg)
    except Exception:
        pass

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        *qt_binaries,
        ('bin/ffmpeg.exe', 'bin'),
    ],
    datas=[
        *qt_datas,
        *perth_datas,
        *chatterbox_datas,
        *runtime_metadata,
    ],
    hiddenimports=[
        *qt_hiddenimports,
        'chatterbox.tts',
        'torchaudio',
        'torchaudio.backend.soundfile_backend',
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'pydub',
        'soundfile',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'gradio',
        'fastapi',
        'starlette',
        'uvicorn',
        'aiohttp',
        'pandas',
        'matplotlib',
        'IPython',
        'jupyter',
        'httpx',
        'anyio',
        'httpcore',
        'sklearn',
        'numba',
        'llvmlite',
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
    name='RealTimeConApp',
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RealTimeConApp',
)