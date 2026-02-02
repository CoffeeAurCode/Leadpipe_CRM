@echo off
cd /d "c:\Users\BIT\Coding\Tenant_management_MVP\frontend"
echo Uninstalling TailwindCSS v4...
call npm uninstall tailwindcss
echo Installing TailwindCSS v3...
call npm install tailwindcss@^3.4.0
echo Done! Please restart the dev server.
pause
