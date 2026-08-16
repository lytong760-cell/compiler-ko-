@echo off
setlocal enabledelayedexpansion
set "KO_HOME=%~dp0"
set "PATH=%KO_HOME%;%PATH%"

if "%~1"=="" (
    ko --help
    exit /b 1
)

if "%~1"=="--install" (
    if "%~2"=="" (
        echo Error: --install requires a module name >&2
        exit /b 1
    )
    echo Installing library: %~2 >&2
    "%KO_HOME%ko_standalone" --install "%~2"
    exit /b %ERRORLEVEL%
)

if "%~1"=="-h" goto :show_help
if "%~1"=="--help" goto :show_help

if "%~1"=="--version" (
    echo ko compiler v2.800
    echo Copyright (c) 2026 ko-studio.ai.studio
    exit /b 0
)

"%KO_HOME%ko_standalone" %*
exit /b %ERRORLEVEL%

:show_help
ko --help
exit /b 0
