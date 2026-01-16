const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let pythonProcess;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true
        },
        titleBarStyle: 'hiddenInset', // macOS native look
        backgroundColor: '#1a1a1a'
    });

    mainWindow.loadFile(path.join(__dirname, 'index.html'));

    // Open DevTools in development
    if (process.env.NODE_ENV === 'development') {
        mainWindow.webContents.openDevTools();
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function startPythonServer() {
    // Use venv python if available, otherwise fall back to system python
    const venvPython = path.join(__dirname, '..', 'venv', 'bin', 'python');
    const pythonPath = process.env.PYTHON_PATH || venvPython;
    const serverScript = path.join(__dirname, '..', 'backend', 'server.py');

    console.log('Starting Python server...');
    console.log('Using Python:', pythonPath);
    pythonProcess = spawn(pythonPath, [serverScript]);

    pythonProcess.stdout.on('data', (data) => {
        console.log(`Python: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        console.error(`Python Error: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);
    });

    // Give the server time to start
    return new Promise(resolve => setTimeout(resolve, 2000));
}

function stopPythonServer() {
    if (pythonProcess) {
        console.log('Stopping Python server...');
        pythonProcess.kill();
        pythonProcess = null;
    }
}

// IPC Handlers

ipcMain.handle('select-file', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile'],
        filters: [
            { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp'] },
            { name: 'ZIP Files', extensions: ['zip'] },
            { name: 'All Files', extensions: ['*'] }
        ]
    });

    if (result.canceled) {
        return null;
    }
    return result.filePaths[0];
});

ipcMain.handle('select-folder', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory']
    });

    if (result.canceled) {
        return null;
    }
    return result.filePaths[0];
});

ipcMain.handle('get-server-url', () => {
    return 'http://localhost:5000';
});

// App lifecycle

app.whenReady().then(async () => {
    await startPythonServer();
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    stopPythonServer();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('quit', () => {
    stopPythonServer();
});

// Handle errors
process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
});

process.on('unhandledRejection', (error) => {
    console.error('Unhandled Rejection:', error);
});
