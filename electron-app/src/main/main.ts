import { app, BrowserWindow, ipcMain } from 'electron'
import path from 'path'

let mainWindow: BrowserWindow | null = null

const PYTHON_API_PORT = 8000

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, '../preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true,
    },
  })

  // Load development or production URL
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    // DevTools can be opened manually with Cmd+Option+I / Ctrl+Shift+I
    // mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function startPythonBackend() {
  // Not used in dev mode - Python is started by start.sh
  // Production builds would need different setup
  console.log('Python backend should already be running via start.sh')
  return Promise.resolve()
}

function stopPythonBackend() {
  // Not needed - start.sh manages the Python process lifecycle
  console.log('Python backend managed by start.sh')
}

app.whenReady().then(async () => {
  // Don't start Python backend - it's already running via start.sh in dev mode
  // Only start it in production builds
  if (process.env.NODE_ENV !== 'development') {
    await startPythonBackend()
  }
  
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  // Only stop Python if we started it (production mode)
  if (process.env.NODE_ENV !== 'development') {
    stopPythonBackend()
  }
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  // Only stop Python if we started it (production mode)
  if (process.env.NODE_ENV !== 'development') {
    stopPythonBackend()
  }
})

// IPC handlers
ipcMain.handle('get-api-url', () => {
  return `http://localhost:${PYTHON_API_PORT}`
})
