import React from 'react';
import { ROUTES } from '../../router/routes';

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
  }

  handleReset = () => {
    this.setState({ hasError: false });
    window.location.assign(ROUTES.HOME);
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-white px-6">
          <div className="max-w-xl w-full bg-white dark:bg-[#131022] rounded-[2rem] p-8 shadow-2xl border border-slate-100 dark:border-white/5">
            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-[#6143f4] mb-3">Frontend Recovery</p>
            <h1 className="text-3xl font-black tracking-tighter uppercase italic leading-tight">
              Something interrupted the page
            </h1>
            <p className="mt-4 text-sm font-medium text-slate-500 dark:text-slate-400 leading-relaxed">
              The app hit a render error. We kept the shell alive so you can recover without a full refresh loop.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={this.handleReset}
                className="px-5 py-3 rounded-xl bg-[#6143f4] text-white text-xs font-black uppercase tracking-[0.2em]"
              >
                Go Home
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-5 py-3 rounded-xl bg-slate-100 dark:bg-white/5 text-xs font-black uppercase tracking-[0.2em] text-slate-700 dark:text-slate-300"
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
