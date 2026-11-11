@echo off
setlocal
cd /d "%~dp0"
title CineRepertorio - Inicializador

echo ==========================================
echo        INICIANDO O CINEREPERTORIO
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD="%CD%\.venv\Scripts\python.exe""
    goto conferir_flask
)
if exist "venv\Scripts\python.exe" (
    set "PYTHON_CMD="%CD%\venv\Scripts\python.exe""
    goto conferir_flask
)

python -c "import flask" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto iniciar
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3 -c "import flask" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
        goto iniciar
    )
    py -3 -m venv .venv
) else (
    where python >nul 2>nul
    if errorlevel 1 goto python_ausente
    python -m venv .venv
)
if errorlevel 1 goto erro_venv
set "PYTHON_CMD="%CD%\.venv\Scripts\python.exe""
echo Instalando as dependencias neste ambiente isolado...
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto erro_pip
goto iniciar

:conferir_flask
%PYTHON_CMD% -c "import flask" >nul 2>nul
if errorlevel 1 (
    echo Flask nao encontrado no ambiente virtual. Instalando dependencias...
    %PYTHON_CMD% -m pip install -r requirements.txt
    if errorlevel 1 goto erro_pip
)

:iniciar
echo.
echo Ambiente Python selecionado:
%PYTHON_CMD% -c "import sys, flask; print(sys.executable); print('Flask', flask.__version__)"
if errorlevel 1 goto erro_flask
if not exist ".env" (
    echo.
    echo AVISO: arquivo .env nao encontrado. O site abre, mas o envio de e-mails fica desativado.
    echo Copie .env.example para .env e configure as credenciais SMTP.
)
echo.
echo Abra http://127.0.0.1:5000 no navegador.
echo Mantenha esta janela aberta enquanto usar o site.
echo Para encerrar o servidor, pressione CTRL+C.
echo.
%PYTHON_CMD% app.py
if errorlevel 1 goto erro_app
exit /b 0

:python_ausente
echo ERRO: Python nao foi encontrado no PATH.
echo Instale Python 3.10 ou superior e marque "Add Python to PATH".
pause
exit /b 1
:erro_venv
echo ERRO: nao foi possivel criar o ambiente virtual.
pause
exit /b 1
:erro_pip
echo ERRO: nao foi possivel instalar as dependencias.
echo Confira a conexao com a internet e execute novamente.
pause
exit /b 1
:erro_flask
echo ERRO: este Python nao consegue importar Flask.
echo Execute: %PYTHON_CMD% -m pip install -r requirements.txt
pause
exit /b 1
:erro_app
echo O servidor foi encerrado com erro. Leia a mensagem acima.
pause
exit /b 1
