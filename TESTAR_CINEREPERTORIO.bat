@echo off
setlocal
cd /d "%~dp0"
title CineRepertorio - Testes
if exist ".venv\Scripts\python.exe" (
  set "PYTHON_CMD="%CD%\.venv\Scripts\python.exe""
  goto executar_testes
)
if exist "venv\Scripts\python.exe" (
  set "PYTHON_CMD="%CD%\venv\Scripts\python.exe""
  goto executar_testes
)
python -c "import flask" >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=python"
  goto executar_testes
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import flask" >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto executar_testes
  )
)
echo Flask nao foi encontrado. Execute INICIAR_CINEREPERTORIO.bat antes.
pause
exit /b 1
:executar_testes
echo === DIAGNOSTICO ===
%PYTHON_CMD% diagnostico.py
if errorlevel 1 goto falha
echo.
echo === TESTES GERAIS ===
%PYTHON_CMD% testes.py
if errorlevel 1 goto falha
echo.
echo === TESTES DO BRIGGS LOCAL (OFFLINE, SEM CUSTO) ===
%PYTHON_CMD% testes_briggs_local.py
if errorlevel 1 goto falha
echo.
echo === TESTES OPCIONAIS DA API (SIMULADOS, SEM CUSTO) ===
%PYTHON_CMD% testes_briggs.py
if errorlevel 1 goto falha
echo.
echo === TESTES DE EMAIL (SMTP SIMULADO) ===
%PYTHON_CMD% testes_email.py
if errorlevel 1 goto falha
echo.
echo Todos os testes disponiveis terminaram sem falhas.
pause
exit /b 0
:falha
echo.
echo Um ou mais testes falharam. Copie a mensagem de erro para diagnostico.
pause
exit /b 1
