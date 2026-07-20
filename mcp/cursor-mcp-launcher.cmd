@echo off
REM Windows launcher for OpenAlgo MCP (Cursor stdio).
REM Prefers native .venv-win; falls back to WSL .venv if needed.
setlocal
set "OA_ROOT=%~dp0.."
set "WIN_PY=%OA_ROOT%\.venv-win\Scripts\python.exe"
set "SCRIPT=%OA_ROOT%\mcp\mcpserver.py"

if exist "%WIN_PY%" (
  "%WIN_PY%" "%SCRIPT%" %*
  exit /b %ERRORLEVEL%
)

REM Fallback: WSL venv (slower; only if .venv-win missing)
wsl.exe -e bash -lc "cd '/mnt/c/Users/TEJA AMBATI/Desktop/openalgo-fresh/openalgo' && exec ./.venv/bin/python ./mcp/mcpserver.py \"$1\" \"$2\"" bash %*
exit /b %ERRORLEVEL%
