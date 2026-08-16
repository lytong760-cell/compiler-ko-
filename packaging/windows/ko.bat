@echo off
REM ko - .ko Language Compiler CLI for Windows
REM Usage: ko [options] <file.ko>

setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "KO_COMPILER=%SCRIPT_DIR%..\ko_compiler.py"
set "MODULES_DIR=%USERPROFILE%\.ko\modules"

REM Ensure modules directory exists
if not exist "%MODULES_DIR%" mkdir "%MODULES_DIR%"

REM Ensure Import.java is compiled
if exist "%SCRIPT_DIR%..\Import.java" (
    if not exist "%SCRIPT_DIR%..\Import.class" (
        javac "%SCRIPT_DIR%..\Import.java" 2>nul || echo Warning: Import.java compilation failed, falling back to Python
    )
)

if "%~1"=="" (
    echo ko - .ko Language Compiler CLI
    echo.
    echo USAGE:
    echo     ko [OPTIONS] ^<file.ko^>
    echo     ko --install ^<module_name^>
    echo.
    echo OPTIONS:
    echo     -h, --help      Show this help message
    echo     --install       Install an external library
    echo     --version       Show version information
    echo.
    echo EXAMPLES:
    echo     ko program.ko                  Run a .ko program
    echo     ko --install MyLibrary         Install an external library
    echo.
    echo For more information, visit: https://ko-studio.ai.studio
    exit /b 1
)

set "SOURCE_FILE="
set "INSTALL_MODULE="

:parse_args
if "%~1"=="" goto :run
if "%~1"=="-h" goto :show_help
if "%~1"=="--help" goto :show_help
if "%~1"=="--version" goto :show_version
if "%~1"=="--install" (
    if "%~2"=="" (
        echo Error: --install requires a module name >&2
        exit /b 1
    )
    set "INSTALL_MODULE=%~2"
    shift
    goto :run
)
set "SOURCE_FILE=%~1"
shift
goto :parse_args

:show_help
echo ko - .ko Language Compiler CLI
echo.
echo USAGE:
echo     ko [OPTIONS] ^<file.ko^>
echo     ko --install ^<module_name^>
echo.
echo OPTIONS:
echo     -h, --help      Show this help message
echo     --install       Install an external library
echo     --version       Show version information
echo.
echo EXAMPLES:
echo     ko program.ko                  Run a .ko program
echo     ko --install MyLibrary         Install an external library
echo.
echo For more information, visit: https://ko-studio.ai.studio
exit /b 0

:show_version
echo ko compiler v2.800
echo Copyright (c) 2026 ko-studio.ai.studio
exit /b 0

:run
REM Handle install mode
if defined INSTALL_MODULE (
    echo Installing library: %INSTALL_MODULE% >&2
    python "%KO_COMPILER%" --install "%INSTALL_MODULE%"
    exit /b %ERRORLEVEL%
)

REM Check source file
if not defined SOURCE_FILE (
    echo Error: No source file specified >&2
    exit /b 1
)

if not exist "%SOURCE_FILE%" (
    echo Error: File not found: %SOURCE_FILE% >&2
    exit /b 1
)

REM Run the compiler
python "%KO_COMPILER%" "%SOURCE_FILE%"
exit /b %ERRORLEVEL%
