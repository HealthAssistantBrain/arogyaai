import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const frontendRoot = path.join(repoRoot, 'apps/frontend');
const routesFile = path.join(frontendRoot, 'src/router/routes.js');
const routerFile = path.join(frontendRoot, 'src/router/index.jsx');
const socketFile = path.join(frontendRoot, 'src/services/dashboardSocketManager.js');
const storeDir = path.join(frontendRoot, 'src/store');

const fail = (message) => {
  console.error(`::error::${message}`);
  process.exitCode = 1;
};

const read = (target) => fs.readFileSync(target, 'utf8');
const routeModule = await import(pathToFileURL(routesFile).href);
const routes = routeModule.ROUTES ?? {};
const routeEntries = Object.entries(routes);

if (!routeEntries.length) {
  fail('ROUTES export is empty.');
}

const invalidRoutes = routeEntries.filter(([, value]) => typeof value !== 'string' || !value.startsWith('/'));
for (const [key, value] of invalidRoutes) {
  fail(`ROUTES.${key} must be an absolute browser path, got ${value}`);
}

const allowedDuplicateAliases = new Set([
  'HOME:LANDING',
  'DEVICES:DEVICE_MANAGER',
  'SLEEP:SLEEP_ANALYSIS',
  'MEDICAL_REPORTS:REPORTS',
  'SECURITY_AUDIT:SETTINGS_PASSWORD',
  'SECURITY_AUDIT:SETTINGS_SECURITY',
  'SETTINGS_DATA:SETTINGS_PRIVACY',
  'SETTINGS_DATA:SETTINGS_DELETE',
  'SETTINGS_PASSWORD:SETTINGS_SECURITY',
  'SETTINGS_SECURITY:SETTINGS_PASSWORD',
  'SETTINGS_DELETE_ACCOUNT:SETTINGS_DELETE',
  'SETTINGS_SECURITY:SECURITY_AUDIT',
]);
const seen = new Map();
for (const [key, value] of routeEntries) {
  if (!seen.has(value)) {
    seen.set(value, key);
    continue;
  }
  const previous = seen.get(value);
  const pair = [previous, key].sort().join(':');
  if (!allowedDuplicateAliases.has(pair)) {
    fail(`Duplicate route value ${value} used by ROUTES.${previous} and ROUTES.${key}`);
  }
}

const routerSource = read(routerFile);
for (const match of routerSource.matchAll(/ROUTES\.([A-Z0-9_]+)/g)) {
  if (!(match[1] in routes)) {
    fail(`Router references missing ROUTES.${match[1]}`);
  }
}

for (const match of routerSource.matchAll(/lazy\(\(\) => import\('([^']+)'\)\)/g)) {
  const importPath = match[1];
  const base = path.resolve(path.dirname(routerFile), importPath);
  const candidates = ['', '.jsx', '.tsx', '.js', '.ts', '/index.jsx', '/index.tsx', '/index.js', '/index.ts'];
  if (!candidates.some((suffix) => fs.existsSync(base + suffix))) {
    fail(`Lazy route import does not resolve: ${importPath}`);
  }
}

const socketSource = read(socketFile);
for (const required of ['new WebSocket', 'scheduleReconnect', 'visibilitychange', '/ws/dashboard/']) {
  if (!socketSource.includes(required)) {
    fail(`Dashboard websocket manager is missing required resilience marker: ${required}`);
  }
}

for (const entry of fs.readdirSync(storeDir)) {
  if (!/\.(js|ts)$/.test(entry)) continue;
  const target = path.join(storeDir, entry);
  const source = read(target);
  if (!source.includes('persist(')) continue;
  if (!source.includes('partialize:') && !source.includes('onRehydrateStorage:')) {
    fail(`Persisted Zustand store must constrain persisted state or handle rehydration: ${entry}`);
  }
  if (source.includes('window.localStorage') && !source.includes('createJSONStorage') && !source.includes('typeof window')) {
    fail(`Persisted Zustand store uses browser storage without a window guard: ${entry}`);
  }
}

const requiredEnv = ['VITE_API_URL', 'VITE_SUPABASE_URL', 'VITE_SUPABASE_ANON_KEY'];
for (const key of requiredEnv) {
  const value = process.env[key] ?? '';
  if (!value || /your_|placeholder|change_me/i.test(value)) {
    fail(`Frontend runtime env is missing or unsafe: ${key}`);
  }
}

if (!process.exitCode) {
  console.log('[FRONTEND] Route, websocket, Zustand hydration, and env contracts passed.');
}
