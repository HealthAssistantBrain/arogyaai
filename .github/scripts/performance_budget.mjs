import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const distDir = path.join(repoRoot, 'apps/frontend/dist');
const maxJsChunkKb = Number(process.env.FRONTEND_MAX_JS_CHUNK_KB ?? 650);
const maxCssChunkKb = Number(process.env.FRONTEND_MAX_CSS_CHUNK_KB ?? 180);
const maxTotalKb = Number(process.env.FRONTEND_MAX_TOTAL_ASSET_KB ?? 2600);

const errors = [];
const assets = [];

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const target = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(target);
    } else if (/\.(js|css)$/.test(entry.name)) {
      const sizeKb = fs.statSync(target).size / 1024;
      assets.push({ file: path.relative(distDir, target).replaceAll('\\', '/'), sizeKb });
    }
  }
}

if (!fs.existsSync(distDir)) {
  console.error(`::error::Frontend dist directory missing: ${distDir}`);
  process.exit(1);
}

walk(distDir);
let totalKb = 0;
for (const asset of assets) {
  totalKb += asset.sizeKb;
  const budget = asset.file.endsWith('.css') ? maxCssChunkKb : maxJsChunkKb;
  if (asset.sizeKb > budget) {
    errors.push(`${asset.file} is ${asset.sizeKb.toFixed(1)}KB, budget is ${budget}KB`);
  }
}

if (totalKb > maxTotalKb) {
  errors.push(`Total JS/CSS payload is ${totalKb.toFixed(1)}KB, budget is ${maxTotalKb}KB`);
}

console.log('[PERFORMANCE] Frontend asset budget report:');
for (const asset of assets.sort((a, b) => b.sizeKb - a.sizeKb)) {
  console.log(`${asset.sizeKb.toFixed(1).padStart(8)} KB  ${asset.file}`);
}
console.log(`[PERFORMANCE] Total JS/CSS: ${totalKb.toFixed(1)} KB`);

if (errors.length) {
  for (const error of errors) {
    console.error(`::error::${error}`);
  }
  process.exit(1);
}

console.log('[PERFORMANCE] Frontend bundle budgets passed.');
