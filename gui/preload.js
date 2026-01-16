const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
    // File selection
    selectFile: () => ipcRenderer.invoke('select-file'),
    selectFolder: () => ipcRenderer.invoke('select-folder'),
    
    // Server URL
    getServerUrl: () => ipcRenderer.invoke('get-server-url'),
    
    // Platform info
    platform: process.platform
});
