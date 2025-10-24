@echo off
echo 🚀 Starting QBO Sankey Dashboard with ngrok...
echo ================================================

REM Check if ngrok is available
where ngrok >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ ngrok not found!
    echo Please install ngrok:
    echo 1. Download from: https://ngrok.com/download
    echo 2. Extract ngrok.exe to a folder
    echo 3. Add that folder to your PATH
    echo 4. Run: ngrok authtoken YOUR_TOKEN
    pause
    exit /b 1
)

echo ✅ ngrok found
echo 🌐 Starting ngrok tunnel...
start /b ngrok http 8050

echo ⏳ Waiting for ngrok to start...
timeout /t 3 /nobreak >nul

echo ✅ ngrok should be running
echo 📋 Next steps:
echo 1. Check ngrok dashboard: http://localhost:4040
echo 2. Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
echo 3. Update Intuit Developer Console with that URL/callback
echo 4. Set NGROK_URL environment variable
echo 5. Start your app with production credentials

echo.
echo Press any key to continue...
pause >nul

REM Activate virtual environment and start app
call .venv\Scripts\activate.bat
python app.py
