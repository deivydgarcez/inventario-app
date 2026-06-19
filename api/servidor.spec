# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para o servidor InvecServidor.exe
# Uso: pyinstaller servidor.spec --clean --noconfirm

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None
hiddenimports = []
datas = []

# Pacotes que precisam de coleta especial
for pkg in ['fastapi', 'uvicorn', 'starlette', 'pydantic', 'pydantic_core',
            'anyio', 'python_jose', 'passlib', 'python_dotenv']:
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

for pkg in ['firebird.driver', 'firebird.base']:
    try:
        tmp = collect_all(pkg)
        datas    += tmp[0]
        hiddenimports += tmp[2]
    except Exception:
        pass

a = Analysis(
    ['server.py'],
    pathex=['.'],
    binaries=[],
    datas=datas + [
        ('app',     'app'),
        ('main.py', '.'),
    ],
    hiddenimports=hiddenimports + [
        'uvicorn.logging',
        'uvicorn.loops.auto',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan.on',
        'anyio._backends._asyncio',
        'jose',
        'jose.jwt',
        'jose.backends',
        'jose.backends.cryptography_backend',
        'cryptography',
        'cryptography.hazmat.primitives.asymmetric.rsa',
        'cryptography.hazmat.primitives.asymmetric.padding',
        'cryptography.hazmat.backends.openssl',
        'passlib.handlers.bcrypt',
        'dotenv',
        'email_validator',
        'h11',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'PIL', 'test'],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='InvecServidor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,   # manter True para ver logs de erro durante deploy
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
