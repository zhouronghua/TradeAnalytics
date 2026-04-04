@echo off
REM Use Python 3 (py launcher). Default "python" on some PCs is still Python 2.
cd /d "%~dp0"
py -3 "%~dp0batch_analyze.py" %*
exit /b %ERRORLEVEL%
