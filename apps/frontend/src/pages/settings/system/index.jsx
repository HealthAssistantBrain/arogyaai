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
            <div className="space-y-2 pb-4 border-b border-[#6143f4]/5">
                <h2 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">System Status</h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-none">Real-time health of ArogyaAI services.</p>
            </div>

            <div className="bg-white dark:bg-[#131022] rounded-[2rem] p-8 shadow-sm border border-[#6143f4]/5 space-y-4">
                <div className="flex items-center justify-between">
                    <span className="text-sm font-bold uppercase tracking-widest text-[#13082a] dark:text-white">API Connection</span>
                    {health.status === 'loading' && <span className="text-xs font-black text-slate-400 uppercase">Checking...</span>}
                    {health.status === 'success' && <span className="text-xs font-black text-emerald-500 uppercase">Operational</span>}
                    {health.status === 'error' && <span className="text-xs font-black text-rose-500 uppercase">Offline</span>}
                </div>
            </div>
        </div>
    );
};
export default SettingsSystem;
