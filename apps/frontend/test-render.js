import fs from 'fs';
import { createServer } from 'vite';

(async () => {
  const vite = await createServer({
    server: { middlewareMode: true },
    appType: 'custom'
  });

  try {
    const module = await vite.ssrLoadModule('/src/pages/GoogleFitSettings.jsx');
    const React = await vite.ssrLoadModule('react');
    const ReactDOMServer = await vite.ssrLoadModule('react-dom/server');
    
    // We mock react-router-dom for SSR
    const RouterMock = await vite.ssrLoadModule('react-router-dom');
    RouterMock.useNavigate = () => (() => {});
    
    const GoogleFitSettings = module.default;
    const html = ReactDOMServer.renderToString(React.createElement(GoogleFitSettings));
    console.log("RENDER_SUCCESS");
  } catch (e) {
    console.error("RENDER_ERROR:", e);
    console.error(e.stack);
  } finally {
    vite.close();
  }
})();
