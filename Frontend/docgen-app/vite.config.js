import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    electron([
      {
        entry: 'electron/main.mjs',
        vite: {
          build: {
            outDir: 'dist/electron',
          },
        },
      },
      {
        entry: 'electron/preload.mjs',
        onstart(options) {
          options.reload()
        },
        vite: {
          build: {
            outDir: 'dist/electron',
          },
        },
      }
    ]),
    renderer(),
  ],
})
