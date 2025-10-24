@echo off
echo 🚀 Starting QBO Sankey Dashboard with ngrok URL...
echo ================================================

REM Set the ngrok URL
set NGROK_URL=https://2bda5df12b82.ngrok-free.app
echo ✅ Set NGROK_URL=%NGROK_URL%

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start the app with the ngrok URL
echo 🚀 Starting app with ngrok support...
python app.py
