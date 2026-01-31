@echo off
REM Add Node.js to PATH for this session
set PATH=%PATH%;C:\Program Files\nodejs

REM Install dependencies
npm install

REM Start the development server
npm run dev

pause
