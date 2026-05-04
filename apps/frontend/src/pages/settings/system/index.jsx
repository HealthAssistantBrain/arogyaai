import { useState, useEffect } from 'react';
import axios from '../../../lib/axios'; // using existing instance

const SettingsSystem = () => {
    const [health, setHealth] = useState({ status: 'loading', data: null });

    useEffect(() => {
        let mounted = true;
        const checkHealth = async () => {
            try {
                // Try fetching health from backend
                const res = await axios.get('/health');
                if (mounted) setHealth({ status: 'success', data: res.data });
            } catch {
                if (mounted) setHealth({ status: 'error', data: null });
            }
        };
        checkHealth();
        return () => { mounted = false; };
    }, []);

    return (
        <div className="max-w-4xl mx-auto space-y-8 pb-16">
            <div className="space-y-2 pb-4 border-b border-primary/5">
                <h2 className="text-3xl font-black text-text-primary dark:text-text-primary tracking-tighter uppercase italic leading-none">System Status</h2>
                <p className="text-sm text-slate-500 dark:text-text-muted font-bold uppercase tracking-tight opacity-80 leading-none">Real-time health of ArogyaAI services.</p>
            </div>

            <div className="bg-surface rounded-[2rem] p-8 shadow-sm border border-primary/5 space-y-4">
                <div className="flex items-center justify-between">
                    <span className="text-sm font-bold uppercase tracking-widest text-text-primary dark:text-text-primary">API Connection</span>
                    {health.status === 'loading' && <span className="text-xs font-black text-text-muted uppercase">Checking...</span>}
                    {health.status === 'success' && <span className="text-xs font-black text-emerald-500 uppercase">Operational</span>}
                    {health.status === 'error' && <span className="text-xs font-black text-rose-500 uppercase">Offline</span>}
                </div>
            </div>
        </div>
    );
};
export default SettingsSystem;

