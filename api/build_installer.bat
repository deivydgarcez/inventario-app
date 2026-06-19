@echo off
title Build - Invec Installer
chcp 65001 >nul
echo.
echo ============================================================
echo   Build do Instalador - Invec API
echo ============================================================
echo.

:: Verificar PyInstaller
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

:: Verificar nssm.exe
if not exist "nssm.exe" (
    echo.
    echo AVISO: nssm.exe nao encontrado nesta pasta.
    echo Baixe em: https://nssm.cc/download
    echo Coloque o nssm.exe aqui e execute este script novamente.
    echo.
    echo O instalador sera compilado sem nssm.exe bundled.
    echo O usuario precisara baixar o nssm.exe separadamente.
    echo.
    pause
)

:: [1/2] Compilar servidor
echo [1/2] Compilando ContadorPontualServidor.exe...
echo       (pode demorar alguns minutos na primeira vez)
echo.
pyinstaller servidor.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERRO ao compilar o servidor.
    pause
    exit /b 1
)
echo.
echo Servidor compilado: dist\ContadorPontualServidor.exe
echo.

:: [2/2] Compilar instalador
echo [2/2] Compilando Instalar-ContadorPontual.exe...
echo.
pyinstaller instalador.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERRO ao compilar o instalador.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   PRONTO!
echo ============================================================
echo.
echo Arquivo gerado: dist\Instalar-ContadorPontual.exe
echo.
echo O que entregar ao cliente:
echo   1. dist\Instalar-ContadorPontual.exe
if exist "nssm.exe" (
    echo   2. nssm.exe ^(ja incluido no instalador^)
) else (
    echo   2. nssm.exe ^(baixar em https://nssm.cc e colocar na mesma pasta^)
)
echo.
echo Como instalar no cliente:
echo   1. Copiar Instalar-ContadorPontual.exe para o PC do cliente
echo   2. Clicar com botao direito ^> Executar como administrador
echo   3. Preencher o caminho do banco .FDB e clicar Instalar
echo.
pause
