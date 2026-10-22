@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo StudyBuddy AI - Demo launcher
echo ============================================
where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10 or newer and try again.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Creating local Python environment...
  python -m venv .venv
  if errorlevel 1 goto error
)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto error
if not exist .env copy .env.example .env >nul
start "StudyBuddy AI server" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8000"
echo Starting the web server...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 30;$i++){ try{$c=New-Object System.Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8000); $c.Close(); $ok=$true; break}catch{Start-Sleep -Seconds 1} }; if(-not $ok){exit 1}"
if errorlevel 1 (
  echo The server did not start. Check the server window for errors.
  pause
  exit /b 1
)
start "" http://127.0.0.1:8000
echo.
echo StudyBuddy AI is ready at http://127.0.0.1:8000
 echo Keep the separate server window open while presenting.
pause
exit /b 0
:error
echo.
echo Setup failed. Check that Python and internet access are available.
pause
exit /b 1
