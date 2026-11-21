@echo off
rem build_msvc.bat — compile the native Aeon panel with MSVC (build.ps1 uses Zig;
rem this is the MSVC equivalent for machines without Zig).
setlocal
set "MSVC=E:\VSBuildTools\VC\Tools\MSVC\14.44.35207"
set "KITS=E:\Windows Kits\10"
set "VER=10.0.22621.0"
set "INCLUDE=%MSVC%\include;%KITS%\Include\%VER%\shared;%KITS%\Include\%VER%\um;%KITS%\Include\%VER%\ucrt"
set "LIB=%MSVC%\lib\x64;%KITS%\Lib\%VER%\um\x64;%KITS%\Lib\%VER%\ucrt\x64"

"%MSVC%\bin\Hostx64\x64\cl.exe" /nologo /std:c++20 /O2 /EHsc /MT /D_UNICODE /DUNICODE /DNOMINMAX /DWIN32_LEAN_AND_MEAN rook.cpp /link /SUBSYSTEM:WINDOWS /ENTRY:wWinMainCRTStartup /OUT:Aeon.exe user32.lib gdi32.lib shell32.lib advapi32.lib bcrypt.lib comctl32.lib
if errorlevel 1 goto :err
echo BUILT Aeon.exe
exit /b 0
:err
echo BUILD FAILED
exit /b 1
