# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec para o Instalar-Invec.exe
# Execute DEPOIS de ter compilado servidor.spec (gera dist/InvecServidor.exe)
# Uso: pyinstaller instalador.spec --clean --noconfirm

import os

block_cipher = None

# Inclui o servidor compilado e o nssm.exe se disponíveis
extra_datas = []

servidor_exe = os.path.join('dist', 'InvecServidor.exe')
if os.path.exists(servidor_exe):
    extra_datas.append((servidor_exe, '.'))
else:
    print(f"AVISO: {servidor_exe} não encontrado. Compile servidor.spec primeiro.")

nssm_exe = 'nssm.exe'
if os.path.exists(nssm_exe):
    extra_datas.append((nssm_exe, '.'))
else:
    print("AVISO: nssm.exe não encontrado na raiz. Baixe em https://nssm.cc e coloque aqui antes de compilar.")

a = Analysis(
    ['instalador.py'],
    pathex=['.'],
    binaries=[],
    datas=extra_datas,
    hiddenimports=["firebird.driver", "firebird.driver.core"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
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
    name='Instalar-Invec',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,       # sem janela de console no instalador
    uac_admin=True,      # pede permissão de admin automaticamente
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
