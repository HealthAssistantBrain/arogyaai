import { Link } from 'react-router-dom';
import { BarChart3, Save, User } from 'lucide-react';
import { ROUTES } from '../router/routes';

export default function OnboardingHeader({ step, onSaveAndExit, loading }) {
    return (
        <header className="flex items-center justify-between border-b border-[#6143f4]/10 px-6 py-4 lg:px-40 bg-white/80 dark:bg-[#131022]/80 backdrop-blur-md sticky top-0 z-50">
            <Link to={ROUTES.LANDING} className="flex items-center gap-3">
                <div className="bg-[#6143f4] p-2 rounded-lg text-white flex items-center justify-center shadow-lg shadow-[#6143f4]/20">
                    <BarChart3 size={20} />
                </div>
                <h2 className="text-[#13082A] dark:text-white text-xl font-bold tracking-tight">ArogyaAI</h2>
            </Link>

            <div className="flex items-center gap-4">
                {onSaveAndExit && (
                    <button
                        type="button"
                        onClick={onSaveAndExit}
                        disabled={loading}
                        className="text-[#6143f4] font-medium hover:bg-[#6143f4]/5 px-4 py-2 rounded-lg transition-colors hidden md:flex items-center gap-2 disabled:opacity-50"
                    >
                        <Save size={18} />
                        Save and Continue later
                    </button>
                )}
                {step && (
                    <div className="text-right hidden sm:block mr-2">
                        <p className="text-xs font-bold text-[#6143f4] uppercase tracking-widest">Onboarding</p>
                        <p className="text-sm text-slate-500 font-medium">
                            {typeof step === 'string' ? step : `Step ${step} of 4`}
                        </p>
                    </div>
                )}
                <div className="h-10 w-10 shrink-0 rounded-full bg-[#6143f4]/10 border border-[#6143f4]/20 flex items-center justify-center overflow-hidden">
                    <User size={20} className="text-[#6143f4]" />
                </div>
            </div>
        </header>
    );
}
