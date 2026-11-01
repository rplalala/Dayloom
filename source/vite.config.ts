import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  base: '/Dayloom/',
  publicDir: false,
  plugins: [react(), {
    name: 'showcase-entry',
    apply: 'build',
    generateBundle: { order: 'post', handler(_, bundle) {
      const html = bundle['showcase.html'];
      if (!html || html.type !== 'asset') throw new Error('Missing showcase HTML');
      delete bundle['showcase.html'];
      html.fileName = 'index.html';
      bundle['index.html'] = html;
      this.emitFile({ type: 'asset', fileName: '.nojekyll', source: '' });
    } },
    closeBundle() {
      cpSync(fileURLToPath(new URL('../dayloom', import.meta.url)),
        fileURLToPath(new URL('./dist/dayloom', import.meta.url)), { recursive: true });
    },
  }],
  build: {
    rollupOptions: { input: fileURLToPath(new URL('./showcase.html', import.meta.url)) },
  },
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', css: true },
});
import { cpSync } from 'node:fs';
