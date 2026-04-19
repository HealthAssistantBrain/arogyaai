import { Blocks } from 'lucide-react';

const SettingsIntegrations = () => {
    return (
        <div className="max-w-5xl mx-auto space-y-12 pb-16">
            <div className="space-y-4 pb-4 border-b border-[#6143f4]/5">
                <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Integrations & Add-ons</h2>
                <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-snug">Connect external platforms, electronic health records (EHR), and third-party analytics pipelines to ArogyaAI.</p>
            </div>

            <div className="bg-slate-50 dark:bg-[#131022] rounded-[3rem] p-16 text-center border border-[#6143f4]/5 shadow-sm">
                <div className="size-20 bg-[#6143f4]/10 rounded-[2rem] mx-auto flex items-center justify-center text-[#6143f4] mb-8 shadow-inner">
                    <Blocks size={40} strokeWidth={2.5} />
                </div>
                <h3 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic mb-4">Marketplace Coming Soon</h3>
                <p className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight max-w-lg mx-auto opacity-70 leading-relaxed">
                    The ArogyaAI Integration Marketplace is currently under development. Soon, you will be able to connect directly to platforms like Epic, Cerner, and Apple HealthKit.
                </p>
            </div>
        </div>
    );
};

export default SettingsIntegrations;
