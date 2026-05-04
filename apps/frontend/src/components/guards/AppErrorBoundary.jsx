import React from 'react';
import { ROUTES } from '../../router/routes';

const ERROR_RETRY_FLAG = 'arogyaai:app-error-boundary-retried';

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    if (typeof console !== 'undefined' && console.error) {
      console.error('[AppErrorBoundary]', error, info);
    }

    if (typeof window !== 'undefined') {
      const hasRetried = window.sessionStorage.getItem(ERROR_RETRY_FLAG) === '1';
      if (!hasRetried) {
        window.sessionStorage.setItem(ERROR_RETRY_FLAG, '1');
        // Auto-reloading hides the underlying React crash and can cause infinite loops.
        // Disabled window.location.reload() to allow the fallback UI to render.
      }
    }
  }

  handleReset = () => {
    window.sessionStorage.removeItem(ERROR_RETRY_FLAG);
    this.setState({ hasError: false });
    window.location.assign(ROUTES.HOME);
  };

  handleManualReload = () => {
    window.sessionStorage.removeItem(ERROR_RETRY_FLAG);
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background dark:bg-background text-text-primary dark:text-text-primary px-6">
          <div className="max-w-xl w-full bg-surface rounded-[2rem] p-8 shadow-2xl border border-slate-100 dark:border-stroke/50">
            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-primary mb-3">Frontend Recovery</p>
            <h1 className="text-3xl font-black tracking-tighter uppercase italic leading-tight">
              Something interrupted the page
            </h1>
            <p className="mt-4 text-sm font-medium text-slate-500 dark:text-text-muted leading-relaxed">
              The app hit a render error. We kept the shell alive so you can recover without a full refresh loop.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={this.handleReset}
                className="px-5 py-3 rounded-xl bg-primary text-white text-xs font-black uppercase tracking-[0.2em]"
              >
                Go Home
              </button>
              <button
                onClick={this.handleManualReload}
                className="px-5 py-3 rounded-xl bg-slate-100 dark:bg-white/5 text-xs font-black uppercase tracking-[0.2em] text-slate-700 dark:text-text-secondary"
              >
                Reload
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default AppErrorBoundary;

