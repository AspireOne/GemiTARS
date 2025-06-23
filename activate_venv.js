const { spawn } = require('child_process');
const path = require('path');

// Path to the activate script
const venvActivate = path.join(__dirname, 'venv', 'Scripts', 'activate.bat');

// Open a new cmd window with the venv activated
spawn('cmd.exe', ['/k', venvActivate], {
  stdio: 'inherit'
});