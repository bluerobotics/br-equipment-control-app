// electron/main.js
const { app, BrowserWindow, ipcMain, net } = require('electron'); // Import ipcMain and net
const path = require('path');
const { spawn, execSync } = require('child_process'); // Import execSync
const waitOn = require('wait-on');
const os = require('os');

let pythonProcess = null;

// This function is critical for finding the correct, working IP address.
function getLocalIp() {
  const nets = os.networkInterfaces();
  for (const name of Object.keys(nets)) {
    for (const net of nets[name]) {
      // Skip over non-IPv4 and internal (i.e. 127.0.0.1) addresses
      if (net.family === 'IPv4' && !net.internal) {
        return net.address;
      }
    }
  }
  return '127.0.0.1'; // Fallback, though the above should work.
}

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 900,
    icon: path.join(__dirname, '../src/assets/logo.png'),
    backgroundColor: '#111827',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const isDev = process.env.NODE_ENV === 'development';
  const devServerURL = 'http://localhost:5173';
  const prodIndexPath = `file://${path.join(__dirname, '../dist/index.html')}`;

  if (isDev) {
    console.log('⏳ Waiting for Vite dev server to start...');
    waitOn({ resources: [devServerURL], timeout: 30000 })
      .then(() => {
        console.log('✅ Vite is ready! Loading URL...');
        mainWindow.loadURL(devServerURL);
        mainWindow.webContents.openDevTools();
      })
      .catch(err => {
        console.error('❌ Vite dev server did not start in time:', err);
      });
  } else {
    mainWindow.loadURL(prodIndexPath);
  }
}

function startPythonBackend() {
  console.log('🐍 Starting Python backend...');

  const pythonExecutable = os.platform() === 'win32' ? 'python' : 'python3';
  const backendDir = path.join(__dirname, '../backend');
  const scriptPath = path.join(backendDir, 'server.py');

  console.log(`🐍 Executable: ${pythonExecutable}`);
  console.log(`🐍 Script Path: ${scriptPath}`);

  const spawnOptions = { 
    cwd: backendDir,
    shell: os.platform() === 'win32' 
  };
  
  pythonProcess = spawn(pythonExecutable, [scriptPath], spawnOptions);

  pythonProcess.stdout.on('data', data => {
    console.log(`[PYTHON STDOUT]: ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', data => {
    console.error(`\n\n🚨 [PYTHON STDERR]: ${data.toString().trim()}\n\n`);
  });

  pythonProcess.on('exit', code => {
    console.log(`🐍 Python process exited with code ${code}`);
  });
  
  pythonProcess.on('error', (err) => {
    console.error('🚨 Failed to start Python process.', err);
  });
}

// --- Function to kill the python process ---
function killPythonProcess() {
  if (pythonProcess) {
    console.log('🔪 Terminating Python process...');
    // Use taskkill on Windows for a more forceful termination
    if (os.platform() === 'win32') {
      try {
        // Use execSync for a blocking, synchronous kill command.
        // This forces Electron to wait until the process is confirmed dead.
        execSync(`taskkill /pid ${pythonProcess.pid} /f /t`);
      } catch (err) {
        // This can throw an error if the process is already gone, which is fine.
        console.log('Python process already terminated.');
      }
    } else {
      pythonProcess.kill();
    }
    pythonProcess = null;
  }
}

// --- NEW: Function to kill the Vite process by port ---
function killViteProcess() {
  // Only run this in development mode
  if (process.env.NODE_ENV !== 'development') {
    return;
  }
  
  console.log('🔪 Terminating Vite process...');
  const vitePort = 5173;
  try {
    if (os.platform() === 'win32') {
      const command = `netstat -aon | findstr ":${vitePort}"`;
      const output = execSync(command).toString();
      const lines = output.trim().split('\n');
      if (lines.length > 0) {
        const parts = lines[0].trim().split(/\s+/);
        const pid = parts[parts.length - 1];
        if (pid && pid !== '0') {
          console.log(`Vite process found with PID: ${pid}. Killing...`);
          execSync(`taskkill /pid ${pid} /f`);
        }
      }
    } else { // macOS and Linux
      const command = `lsof -i tcp:${vitePort} | grep LISTEN | awk '{print $2}'`;
      const pid = execSync(command).toString().trim();
      if (pid) {
        console.log(`Vite process found with PID: ${pid}. Killing...`);
        execSync(`kill -9 ${pid}`);
      }
    }
  } catch (err) {
    console.log('Vite process not found or already terminated.');
  }
}


app.whenReady().then(() => {
  // --- Use the local network IP for main process requests ---
  ipcMain.handle('api-request', async (event, { endpoint, options }) => {
    // Using the getLocalIp() function is required for this specific machine's
    // network configuration to work correctly.
    const ip = getLocalIp();
    const url = `http://${ip}:5000/api/${endpoint}`;
    console.log(`📡 IPC: Handling api-request for: ${url}`);
    
    return new Promise((resolve, reject) => {
      const request = net.request({
        method: options.method || 'GET',
        url: url,
        headers: options.headers,
      });

      let body = '';
      request.on('response', (response) => {
        response.on('data', (chunk) => {
          body += chunk.toString();
        });
        response.on('end', () => {
          try {
            const parsedBody = JSON.parse(body);
            if (response.statusCode >= 200 && response.statusCode < 300) {
              resolve(parsedBody);
            } else {
              reject(parsedBody.error || `HTTP Error: ${response.statusCode}`);
            }
          } catch (e) {
            reject(`Failed to parse JSON response: ${e.message}. Received: ${body.substring(0, 100)}...`);
          }
        });
        response.on('error', (error) => {
          reject(`Response error: ${error.message}`);
        });
      });

      request.on('error', (error) => {
        reject(`Request failed: ${error.message}`);
      });
      
      if (options.body) {
        request.write(options.body);
      }

      request.end();
    });
  });

  console.log('🚀 Electron app is ready');
  startPythonBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  // On macOS it's common for applications and their menu bar
  // to stay active until the user quits explicitly with Cmd + Q
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// --- More robust cleanup ---
// This will run when the app is quitting, for example,
// by closing the window, using Cmd+Q, or calling app.quit().
app.on('will-quit', () => {
  killPythonProcess();
  killViteProcess(); // Also kill the Vite server
});

// --- FINAL FIX: Explicitly handle Ctrl+C in the terminal ---
// This ensures the Python process is killed when you stop the dev server.
process.on('SIGINT', () => {
    console.log('SIGINT signal received. Initiating graceful shutdown...');
    // Trigger Electron's own shutdown procedure. This will eventually
    // fire the 'will-quit' event where our cleanup function lives.
    app.quit();
});
