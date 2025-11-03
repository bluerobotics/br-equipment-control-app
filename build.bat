@echo off
REM Build script for Windows

echo Building BR Equipment Control App...
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo PyInstaller is not installed.
    echo Installing PyInstaller...
    pip install pyinstaller
    echo.
)

REM Build the executable
echo Running PyInstaller...
pyinstaller build.spec

if errorlevel 1 (
    echo.
    echo Build failed! Check the error messages above.
    pause
    exit /b 1
)

echo.
echo Build complete!
echo Executable location: dist\BR-Equipment-Control\BR-Equipment-Control.exe
echo.
echo Creating zip archive...
cd dist
powershell -Command "Compress-Archive -Path 'BR-Equipment-Control' -DestinationPath 'BR-Equipment-Control-Windows.zip' -Force"
cd ..

echo.
echo Done! Distributable zip file created at:
echo   dist\BR-Equipment-Control-Windows.zip
echo.
pause

