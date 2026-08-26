import { contextBridge, ipcRenderer } from 'electron';

/**
 * Preload script — exposes a safe, sandboxed `window.electronAPI` object
 * to the renderer process via context bridge. No Node.js globals leak.
 */
contextBridge.exposeInMainWorld('electronAPI', {
  // ── File dialogs ──────────────────────────────────────────────────────
  /** Open a native file picker dialog. Returns { filePath, fileName, fileSize } or null. */
  openFileDialog: (options) => ipcRenderer.invoke('dialog:openFile', options),

  /** Open a native save-as dialog and write the downloaded buffer. Returns boolean. */
  saveFile: ({ defaultName, buffer }) =>
    ipcRenderer.invoke('dialog:saveFile', { defaultName, buffer }),

  /** Read a file from disk into an ArrayBuffer (for uploading to backend). */
  readFileBuffer: (filePath) => ipcRenderer.invoke('file:readBuffer', filePath),

  // ── Shell ─────────────────────────────────────────────────────────────
  /** Open a URL in the user's default browser. */
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),

  // ── App info ──────────────────────────────────────────────────────────
  /** Get the app version from package.json. */
  getVersion: () => ipcRenderer.invoke('app:getVersion'),

  // ── Menu events (main → renderer) ────────────────────────────────────
  /** Listen for the "New Session" menu item / Cmd+N. */
  onNewSession: (callback) => {
    ipcRenderer.on('menu:newSession', callback);
    return () => ipcRenderer.removeListener('menu:newSession', callback);
  },

  // ── Platform info ─────────────────────────────────────────────────────
  platform: process.platform,
});
