import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // GitHub Pages serves this repository below /<repository-name>/.
  // Local development keeps the root path for the existing preview URL.
  base: process.env.GITHUB_ACTIONS ? '/regulatory-interpretation-workbench/' : '/',
})
