import zipfile
import os
import sys
import stat


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

echo ==========================================
echo   ko Compiler v2.800 Installer
echo ==========================================
echo.

set "INSTALL_DIR=%USERPROFILE%\\.ko"
echo This will install the .ko compiler to: %INSTALL_DIR%
echo.

REM ==========================================
REM Step 1: Check Java runtime
REM ==========================================
echo [1/5] Checking Java runtime...
java -version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Java runtime not found.
    echo This compiler requires Java 11 or higher.
    echo.

    set /p DOWNLOAD_JAVA="Download and install Java 17 now? [Y/n]: "
    if /i "!DOWNLOAD_JAVA!"=="Y" (
        echo.
        echo [2/5] Downloading Java 17...

        set "JAVA_INSTALLER=%TEMP%\\OpenJDK17_x64.msi"
        powershell -Command "& {try { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.msi' -OutFile '%JAVA_INSTALLER%' -UseBasicParsing; exit 0} catch { exit 1 }}"

        if exist "%JAVA_INSTALLER%" (
            echo.
            echo [3/5] Installing Java 17...
            echo This may take a few minutes...
            msiexec /i "%JAVA_INSTALLER%" /qn /norestart ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJavaHome,FeatureOracleJavaSoft INSTALLDIR="C:\\Program Files\\Eclipse Adoptium\\jdk-17" >nul 2>&1

            REM Add Java to system PATH
            setx PATH "C:\\Program Files\\Eclipse Adoptium\\jdk-17\\bin;%PATH%" /M >nul 2>&1

            REM Clean up installer
            del "%JAVA_INSTALLER%" >nul 2>&1

            echo.
            echo [4/5] Java installed successfully!
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
) else (
    echo Java runtime detected.
)

REM ==========================================
REM Step 2: Extract files
REM ==========================================
echo.
echo [2/5] Extracting files...
set "EXTRACT_DIR=%TEMP%\\ko_install_%RANDOM%"
mkdir "%EXTRACT_DIR%" >nul 2>&1
powershell -Command "Expand-Archive -Path '%~f0' -DestinationPath '%EXTRACT_DIR%' -Force" >nul 2>&1

REM ==========================================
REM Step 3: Install files
REM ==========================================
echo [3/5] Installing...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
xcopy /E /I /Y "%EXTRACT_DIR%\\*" "%INSTALL_DIR%\\" >nul

REM ==========================================
REM Step 4: Add to PATH
REM ==========================================
echo [4/5] Configuring PATH...
setx PATH "%INSTALL_DIR%;%PATH%" >nul 2>&1

REM ==========================================
REM Step 5: Cleanup
REM ==========================================
echo [5/5] Cleaning up...
rmdir /S /Q "%EXTRACT_DIR%" >nul 2>&1

echo.
echo ==========================================
echo   Installation Complete!
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
