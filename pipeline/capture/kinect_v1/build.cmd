@echo off
rem Build KinectCapture.exe with the C# compiler that ships with Windows (.NET Framework 4.x, C# 5).
rem Needs the Kinect for Windows SDK 1.8 (sets KINECTSDK10_DIR). No Visual Studio required.
setlocal
cd /d "%~dp0"

set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%CSC%" (
  echo .NET Framework 4 C# compiler not found under %WINDIR%\Microsoft.NET. Enable .NET Framework 4.8 in Windows Features.
  exit /b 1
)

set "KINECT=%KINECTSDK10_DIR%Assemblies\Microsoft.Kinect.dll"
if not exist "%KINECT%" set "KINECT=%ProgramFiles%\Microsoft SDKs\Kinect\v1.8\Assemblies\Microsoft.Kinect.dll"
if not exist "%KINECT%" (
  echo Microsoft.Kinect.dll not found. Install the Kinect for Windows SDK 1.8 ^(KinectSDK-v1.8-Setup.exe^) and reopen this window.
  exit /b 1
)

"%CSC%" /nologo /optimize+ /warnaserror+ /out:KinectCapture.exe /r:"%KINECT%" /r:System.Drawing.dll KinectCapture.cs
if errorlevel 1 (
  echo.
  echo Build failed. KinectCapture.cs was written against the SDK 1.8 API as declared in api_stub\MicrosoftKinectStub.cs;
  echo a compile error naming a Kinect member means the real SDK differs there. Please report the message.
  exit /b 1
)
copy /y "%KINECT%" . >nul
echo Built KinectCapture.exe. Record with:  KinectCapture.exe C:\recordings\session01 --seconds 40
