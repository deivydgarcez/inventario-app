@echo off
setlocal EnableDelayedExpansion
title Instalador - Invec API
chcp 65001 >nul

:: ─── Admin ───────────────────────────────────────────────────────────────────
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Solicitando permissao de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo ============================================================
echo   Instalador - Invec API  (modo script)
echo ============================================================
echo.

:: ─── Python ──────────────────────────────────────────────────────────────────
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: Python nao encontrado.
    echo.
    echo Instale o Python 3.11+ em: https://python.org/downloads
    echo Marque a opcao "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

:: ─── NSSM ────────────────────────────────────────────────────────────────────
set "SCRIPT_DIR=%~dp0"
if not exist "%SCRIPT_DIR%nssm.exe" (
    echo AVISO: nssm.exe nao encontrado em %SCRIPT_DIR%
    echo.
    echo Baixe o nssm.exe em: https://nssm.cc/download
    echo Coloque nssm.exe na mesma pasta deste instalador e execute novamente.
    pause
    exit /b 1
)

:: ─── Coletar configuracoes ───────────────────────────────────────────────────
echo Preencha as informacoes abaixo (pressione Enter para usar o valor padrao):
echo.

set /p "DB_PATH=Caminho completo do banco Firebird (.FDB): "
if "!DB_PATH!"=="" (
    echo ERRO: caminho do banco e obrigatorio.
    pause
    exit /b 1
)

set "FB_HOST=localhost"
set /p "FB_HOST=Host Firebird [localhost]: "
if "!FB_HOST!"=="" set FB_HOST=localhost

set "FB_USER=SYSDBA"
set /p "FB_USER=Usuario Firebird [SYSDBA]: "
if "!FB_USER!"=="" set FB_USER=SYSDBA

set "FB_PASS=masterkey"
set /p "FB_PASS=Senha Firebird [masterkey]: "
if "!FB_PASS!"=="" set FB_PASS=masterkey

set "PORT=8000"
set /p "PORT=Porta da API [8000]: "
if "!PORT!"=="" set PORT=8000

set "INSTALL_DIR=%SCRIPT_DIR%"
echo.
echo Instalando em: %INSTALL_DIR%
echo.

:: ─── .env ────────────────────────────────────────────────────────────────────
echo Salvando configuracao...
(
    echo FB_DATABASE=!DB_PATH!
    echo FB_HOST=!FB_HOST!
    echo FB_USER=!FB_USER!
    echo FB_PASSWORD=!FB_PASS!
    echo PORT=!PORT!
) > "%INSTALL_DIR%.env"

:: ─── pip ─────────────────────────────────────────────────────────────────────
echo Instalando dependencias Python...
python -m pip install -r "%INSTALL_DIR%requirements.txt" --quiet
if %ERRORLEVEL% NEQ 0 (
    echo ERRO ao instalar dependencias pip.
    pause
    exit /b 1
)

:: ─── Servico Windows ─────────────────────────────────────────────────────────
echo Configurando servico Windows...

:: Remover servico anterior se existir
"%INSTALL_DIR%nssm.exe" stop  InvecAPI >nul 2>&1
"%INSTALL_DIR%nssm.exe" remove InvecAPI confirm >nul 2>&1

:: Obter caminho do Python
for /f "tokens=*" %%i in ('where python') do (
    set "PYTHON_EXE=%%i"
    goto :got_python
)
:got_python

set "SERVER_SCRIPT=%INSTALL_DIR%server.py"

:: Instalar servico
"%INSTALL_DIR%nssm.exe" install InvecAPI "!PYTHON_EXE!" "!SERVER_SCRIPT!"
"%INSTALL_DIR%nssm.exe" set InvecAPI AppDirectory    "%INSTALL_DIR%"
"%INSTALL_DIR%nssm.exe" set InvecAPI DisplayName     "Invec - API Inventario"
"%INSTALL_DIR%nssm.exe" set InvecAPI Description     "API de inventario - Invec Tecnologia"
"%INSTALL_DIR%nssm.exe" set InvecAPI Start           SERVICE_AUTO_START
mkdir "%INSTALL_DIR%logs" >nul 2>&1
"%INSTALL_DIR%nssm.exe" set InvecAPI AppStdout       "%INSTALL_DIR%logs\servico.log"
"%INSTALL_DIR%nssm.exe" set InvecAPI AppStderr       "%INSTALL_DIR%logs\erro.log"
"%INSTALL_DIR%nssm.exe" set InvecAPI AppRotateFiles  1
"%INSTALL_DIR%nssm.exe" set InvecAPI AppRotateBytes  10485760

:: ─── Firewall ────────────────────────────────────────────────────────────────
echo Abrindo porta no firewall...
netsh advfirewall firewall delete rule name="InvecAPI" >nul 2>&1
netsh advfirewall firewall add rule ^
    name="InvecAPI" dir=in action=allow ^
    protocol=TCP localport=!PORT! profile=domain,private,public >nul

:: ─── Iniciar ─────────────────────────────────────────────────────────────────
echo Iniciando servico...
"%INSTALL_DIR%nssm.exe" start InvecAPI

echo.
echo ============================================================
echo   Instalacao concluida!
echo   API disponivel em: http://localhost:!PORT!
echo ============================================================
echo.
pause
