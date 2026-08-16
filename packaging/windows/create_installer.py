import zipfile
import os
import sys

def create_windows_installer():
    source_dir = sys.argv[1]
    output_file = sys.argv[2]
    
    zip_file = output_file.replace('.exe', '.zip')
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                if file.endswith('.pyc') or file == 'create_installer.py':
                    continue
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, source_dir)
                zf.write(filepath, arcname)
    
    batch_stub = b'''@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
set "INSTALL_DIR=%USERPROFILE%\\.ko"
set "PATH=%INSTALL_DIR%;%PATH%"

echo ==========================================
echo   ko Compiler v2.800 Installer
echo ==========================================
echo.

REM Check if Java runtime is available
echo [1/4] Checking Java runtime...
java -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Java runtime not found.
    echo This compiler requires Java 11 or higher.
    echo.
    set /p DOWNLOAD_JAVA="Do you want to download and install Java now? (Y/N): "
    if /i "!DOWNLOAD_JAVA!"=="Y" (
        echo.
        echo [2/4] Downloading Java...
        set "JAVA_INSTALLER=%TEMP%\\OpenJDK17_x64.msi"
        echo Downloading from Adoptium...
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.msi' -OutFile '%JAVA_INSTALLER%' -UseBasicParsing"
        
        if exist "%JAVA_INSTALLER%" (
            echo.
            echo [3/4] Installing Java...
            echo This may take a few minutes...
            msiexec /i "%JAVA_INSTALLER%" /qn /norestart ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJavaHome,FeatureOracleJavaSoft INSTALLDIR="C:\\Program Files\\Eclipse Adoptium\\jdk-17"
            
            REM Update PATH
            setx PATH "C:\\Program Files\\Eclipse Adoptium\\jdk-17\\bin;%PATH%" >nul 2>&1
            
            REM Clean up
            del "%JAVA_INSTALLER%" >nul 2>&1
            
            echo.
            echo [4/4] Java installed successfully!
            echo Please restart this installer to continue.
            echo.
            pause
            exit /b 0
        ) else (
            echo.
            echo ERROR: Failed to download Java installer.
            echo Please download Java manually from:
            echo   https://adoptium.net/temurin/releases/
            echo   https://www.java.com/download/
            echo.
            pause
            exit /b 1
        )
    ) else (
        echo.
        echo Please install Java manually from:
        echo   https://adoptium.net/temurin/releases/
        echo   https://www.java.com/download/
        echo.
        echo After installing Java, run this installer again.
        echo.
        pause
        exit /b 1
    )
)

REM Check Java version
echo Java runtime detected.
echo.

REM Extract files
echo [2/4] Extracting files...
set "EXTRACT_DIR=%TEMP%\\ko_install_%RANDOM%"
mkdir "%EXTRACT_DIR%" >nul 2>&1
powershell -Command "Expand-Archive -Path '%~f0' -DestinationPath '%EXTRACT_DIR%' -Force" >nul 2>&1

REM Install
echo [3/4] Installing...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
xcopy /E /I /Y "%EXTRACT_DIR%\\*" "%INSTALL_DIR%\\" >nul
rmdir /S /Q "%EXTRACT_DIR%" >nul 2>&1

REM Add to PATH if not already there
echo [4/4] Configuring PATH...
setx PATH "%PATH%;%INSTALL_DIR%" >nul 2>&1

echo.
echo ==========================================
echo   Installation complete!
echo ==========================================
echo.
echo You can now use 'ko' from anywhere in the terminal.
echo.
echo To get started:
echo   ko --help
echo   ko program.ko
echo.
pause
exit /b 0
'''
    
    with open(zip_file, 'rb') as f:
        zip_content = f.read()
    
    with open(output_file, 'wb') as f:
        f.write(batch_stub + zip_content)
    
    os.remove(zip_file)
    print(f"Created: {output_file}")

if __name__ == '__main__':
    create_windows_installer()
