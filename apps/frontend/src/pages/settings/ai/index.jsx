import { BrainCircuit } from 'lucide-react';

const SettingsAI = () => {
    return (
        <div className="max-w-5xl mx-auto space-y-12 pb-16">
            <div className="space-y-4 pb-4 border-b border-primary/5">
                <h2 className="text-5xl font-black text-text-primary dark:text-text-primary tracking-tighter uppercase italic leading-none">AI & Forecasting Preferences</h2>
                <p className="text-lg text-slate-500 dark:text-text-muted font-bold uppercase tracking-tight opacity-80 leading-snug">Tune the behavior, verbosity, and clinical threshold of the ArogyaAI predictive models.</p>
            </div>

            <div className="bg-slate-50 dark:bg-card rounded-[3rem] p-16 text-center border border-secondary/5 shadow-sm">
                <div className="size-20 bg-secondary/10 rounded-[2rem] mx-auto flex items-center justify-center text-secondary mb-8 shadow-inner">
                    <BrainCircuit size={40} strokeWidth={2.5} />
                </div>
                <h3 className="text-2xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter italic mb-4">Advanced Model Tuning</h3>
                <p className="text-sm font-bold text-slate-500 dark:text-text-muted uppercase tracking-tight max-w-lg mx-auto opacity-70 leading-relaxed">
                    Custom diagnostic weights and deterministic boundaries are currently locked to clinical defaults to ensure baseline accuracy. Personalized LLM tuning will unlock in v3.1.
                </p>
            </div>
        </div>
    );
};

export default SettingsAI;

