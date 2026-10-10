// Turns dist/index.html into the page published online (publish/index.html):
// styles inlined, app code served next to it as assets/app.js.
import { readFileSync, writeFileSync, mkdirSync, copyFileSync } from 'node:fs';

const html = readFileSync('dist/index.html', 'utf8');
const title = html.match(/<title>(.*?)<\/title>/)[1];
const cssHref = html.match(/<link rel="stylesheet"[^>]*href="\.\/([^"]+)"/)[1];
const css = readFileSync(`dist/${cssHref}`, 'utf8');
const body = html.match(/<body>([\s\S]*)<\/body>/)[1].trim();

mkdirSync('publish/assets', { recursive: true });
copyFileSync('dist/assets/app.js', 'publish/assets/app.js');
writeFileSync(
  'publish/index.html',
  `<title>${title}</title>\n<style>${css}</style>\n${body}\n<script type="module" src="assets/app.js"></script>\n`,
);
console.log('publish/index.html ready');
