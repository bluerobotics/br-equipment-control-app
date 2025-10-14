// electron/preload.js
const { contextBridge, ipcRenderer } = require('electron');

// Expose a secure API to the renderer process (your Vue app)
contextBridge.exposeInMainWorld('electron', {
  // --- NEW: Expose a function to make API requests via the main process ---
  apiRequest: (endpoint, options) => ipcRenderer.invoke('api-request', { endpoint, options })
});
