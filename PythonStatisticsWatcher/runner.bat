@echo off
:loop
python main.py
if %ERRORLEVEL%==14 (
    echo Restarting program...
    goto loop
) else (
    echo Program exited with code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)