@echo off
REM One-command setup for Windows. Double-click this file.
REM Windows won't give Claude an independent on-screen cursor without a second
REM login session, so the no-conflict version runs a private Linux desktop in
REM Docker that you watch in the browser. Your real mouse/keyboard stay yours.
setlocal
cd /d "%~dp0\.."

where claude >nul 2>&1 || (echo Claude Code is not installed. Install it, then run this again. & pause & exit /b 1)
where docker >nul 2>&1 || (echo Docker Desktop is not installed. Get it from https://www.docker.com/products/docker-desktop/ , start it, then run this again. & pause & exit /b 1)

docker info >nul 2>&1 || (echo Docker Desktop is installed but not running. Start Docker Desktop and wait for it to say "running", then run this again. & pause & exit /b 1)

echo.
echo ==^> Building Claude's private desktop ^(first run takes a few minutes^)
docker compose up -d --build || (echo Build failed. See the messages above. & pause & exit /b 1)

echo.
echo ==^> Connecting it to Claude Code
claude mcp remove sidecar-desktop >nul 2>&1
claude mcp add --transport http --scope user sidecar-desktop http://127.0.0.1:8765/mcp

echo.
echo   All set.
echo.
echo   Claude now has 'sidecar-desktop' tools in every Claude Code session, with
echo   its OWN screen - your real mouse and keyboard stay yours.
echo.
echo   Watch it work:  http://localhost:6080/vnc.html
echo.
echo   Note: this desktop runs Linux apps (its own Firefox), not your installed
echo   Windows programs. See the README if you need Windows-native apps.
echo.
start "" http://localhost:6080/vnc.html
pause
