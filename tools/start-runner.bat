@echo off
rem Dalal Desk desktop runner. Put this file in your trading folder, next to the dalal-desk folder,
rem then double-click it. Leave the window open while Claude works; close it to stop.
cd /d "%~dp0"
where py >nul 2>nul && (py -3 dalal-desk\tools\runner.py --work "%~dp0." & goto :end)
where python >nul 2>nul && (python dalal-desk\tools\runner.py --work "%~dp0." & goto :end)
if exist "%USERPROFILE%\anaconda3\python.exe" ("%USERPROFILE%\anaconda3\python.exe" dalal-desk\tools\runner.py --work "%~dp0." & goto :end)
echo Python 3 was not found. Install it from python.org and tick "Add python.exe to PATH".
:end
pause
