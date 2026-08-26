import { app, BrowserWindow, ipcMain, dialog, shell, Menu, nativeTheme } from 'electron';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Paths
const DIST = path.join(__dirname, '../dist');
const VITE_DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL;

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 860,
    minWidth: 900,
    minHeight: 600,
    title: 'DocGen',
    titleBarStyle: 'hiddenInset',    // macOS: native traffic lights, content extends under title bar
    trafficLightPosition: { x: 16, y: 18 },
    backgroundColor: '#ffffff',
    show: false,                     // Show after ready-to-show to avoid flash
    webPreferences: {
      preload: path.join(__dirname, 'preload.mjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  // Smooth show
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Load app
  if (VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(VITE_DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(DIST, 'index.html'));
  }
}

// ── IPC Handlers ───────────────────────────────────────────────────────────

// Native file open dialog
ipcMain.handle('dialog:openFile', async (_event, options) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Choose a document',
    filters: [
      { name: 'Documents', extensions: ['pdf', 'docx', 'pptx', 'txt', 'md', 'csv'] },
      { name: 'All Files', extensions: ['*'] },
    ],
    properties: ['openFile'],
    ...options,
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  const filePath = result.filePaths[0];
  const stats = fs.statSync(filePath);
  return {
    filePath,
    fileName: path.basename(filePath),
    fileSize: stats.size,
  };
});

// Native save dialog + write downloaded blob
ipcMain.handle('dialog:saveFile', async (_event, { defaultName, buffer }) => {
  const ext = path.extname(defaultName).replace('.', '');
  const filterMap = {
    docx: { name: 'Word Document', extensions: ['docx'] },
    pptx: { name: 'PowerPoint', extensions: ['pptx'] },
    pdf:  { name: 'PDF Document', extensions: ['pdf'] },
  };
  const filter = filterMap[ext] || { name: 'File', extensions: [ext || '*'] };

  const result = await dialog.showSaveDialog(mainWindow, {
    title: 'Save generated document',
    defaultPath: defaultName,
    filters: [filter],
  });
  if (result.canceled || !result.filePath) return false;
  fs.writeFileSync(result.filePath, Buffer.from(buffer));
  // Show in Finder / File Explorer
  shell.showItemInFolder(result.filePath);
  return true;
});

// Read file into buffer for upload
ipcMain.handle('file:readBuffer', async (_event, filePath) => {
  const buffer = fs.readFileSync(filePath);
  return buffer;
});

// Open external URL
ipcMain.handle('shell:openExternal', async (_event, url) => {
  shell.openExternal(url);
});

// Get app version
ipcMain.handle('app:getVersion', () => app.getVersion());

// ── App Menu ────────────────────────────────────────────────────────────────

function buildMenu() {
  const isMac = process.platform === 'darwin';
  const template = [
    ...(isMac ? [{
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    }] : []),
    {
      label: 'File',
      submenu: [
        {
          label: 'New Session',
          accelerator: 'CmdOrCtrl+N',
          click: () => mainWindow?.webContents.send('menu:newSession'),
        },
        { type: 'separator' },
        isMac ? { role: 'close' } : { role: 'quit' },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' }, { role: 'redo' }, { type: 'separator' },
        { role: 'cut' }, { role: 'copy' }, { role: 'paste' },
        ...(isMac ? [{ role: 'pasteAndMatchStyle' }, { role: 'delete' }, { role: 'selectAll' }]
                   : [{ role: 'delete' }, { type: 'separator' }, { role: 'selectAll' }]),
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        ...(isMac ? [{ type: 'separator' }, { role: 'front' }] : [{ role: 'close' }]),
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

// ── App lifecycle ──────────────────────────────────────────────────────────

app.whenReady().then(() => {
  buildMenu();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
