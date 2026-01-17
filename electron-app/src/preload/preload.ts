import { contextBridge, ipcRenderer } from 'electron'

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  getApiUrl: () => ipcRenderer.invoke('get-api-url'),
  platform: process.platform,
})

// TypeScript declarations for the exposed API
declare global {
  interface Window {
    electronAPI: {
      getApiUrl: () => Promise<string>
      platform: string
    }
  }
}
