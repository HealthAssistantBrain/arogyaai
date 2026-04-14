import { useNavigate } from 'react-router-dom';
import {
    FlaskConical,
    Moon,
    Search,
    Sparkles,
    Utensils,
    Dumbbell,
    ArrowRight,
    AlarmClock,
    Thermometer,
    CalendarDays,
    Wind,
    Bell,
    Brain,
    Activity,
} from 'lucide-react';
import { ROUTES } from '../router/routes';
import { openCommandPalette } from '../components/CommandPalette';

const PreventiveRecommendations = () => {
    const navigate = useNavigate();

    const lifestyleImprovements = [
        {
            icon: Brain,
            title: 'Stress Management',
            description:
                'Implement 10-min box breathing twice daily to lower cortisol levels which are currently elevated.',
            color: 'text-[#6143f4]',
            bgColor: 'bg-[#6143f4]/10',
        },
        {
            icon: Activity,
            title: 'Cessation Support',
            description:
                'Continue your nicotine-free streak. Your lung capacity has improved by 12% in the last 30 days.',
            color: 'text-[#009cde]',
            bgColor: 'bg-[#009cde]/10',
        },
    ];

    const dietaryOptimization = [
        {
            title: 'Mediterranean Shift',
            description: 'Increase intake of extra virgin olive oil and leafy greens.',
            priority: 'High Priority',
            priorityColor: 'text-[#009cde] bg-[#009cde]/10',
            borderColor: 'border-l-4 border-[#009cde]',
        },
        {
            title: 'Sodium Regulation',
            description: 'Keep daily sodium intake below 2,300mg to stabilize blood pressure.',
            priority: 'Standard',
            priorityColor: 'text-slate-400 bg-slate-100',
            borderColor: '',
        },
    ];

    const labTests = [
        {
            name: 'HbA1c & Fasting Insulin',
            category: 'Metabolic Health Marker',
            reason: 'To monitor blood glucose regulation after recent dietary changes.',
            date: 'Oct 15, 2024',
        },
        {
            name: 'Lipid Profile (ApoB focus)',
            category: 'Cardiovascular Screening',
            reason: 'ApoB provides a more accurate measure of atherogenic risk than LDL-C alone.',
            date: 'Nov 02, 2024',
        },
        {
            name: 'Vitamin D (25-OH)',
            category: 'Immune & Bone Health',
            reason:
                'Verify if the current supplementation dose is sufficient for target range (50-80 ng/mL).',
            date: 'Oct 15, 2024',
        },
    ];

    return (
        <div className="flex-1 flex flex-col min-w-0 bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen antialiased">
            {/* Top Header */}
            <header className="h-20 bg-white/80 dark:bg-[#131022]/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 px-8 flex items-center justify-between sticky top-0 z-40 shrink-0">
                <div className="relative w-full max-w-md group">
                    <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} 
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors"
                        size={18}
                    />
                    <input
                        className="w-full bg-slate-100 dark:bg-white/5 border-none rounded-xl py-2.5 pl-11 pr-4 text-sm font-medium focus:ring-2 focus:ring-[#6143f4]/20 transition-all outline-none text-[#13082a] dark:text-white"
                        placeholder="Search insights, labs, or metrics..."
                        type="text"
                    />
                </div>
                <div className="flex items-center gap-4">
                    <button className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-300 relative shadow-inner active:scale-90 transition-all" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                        <Bell size={20} />
                        <span className="absolute top-2.5 right-2.5 size-2 bg-[#6143f4] rounded-full border-2 border-white dark:border-[#131022]"></span>
                    </button>
                    <div
                        className="flex items-center gap-3 pl-4 border-l border-slate-200 dark:border-slate-800 cursor-pointer group"
                        onClick={() => navigate(ROUTES.SETTINGS)}
                    >
                        <div className="text-right hidden sm:block">
                            <p className="text-sm font-black text-[#13082a] dark:text-white group-hover:text-[#6143f4] transition-colors">
                                Alex Johnson
                            </p>
                            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-0.5">
                                Premium Member
                            </p>
                        </div>
                        <div className="size-10 rounded-full border-2 border-[#6143f4] overflow-hidden shadow-lg group-hover:scale-110 transition-transform bg-[#6143f4]/20 flex items-center justify-center text-[#6143f4] font-bold text-sm">
                            AJ
                        </div>
                    </div>
                </div>
            </header>

            {/* Page Content */}
            <div className="p-8 max-w-7xl mx-auto w-full space-y-12">
                {/* Title */}
                <div className="max-w-4xl">
                    <h2 className="text-4xl lg:text-5xl font-black tracking-tight text-[#13082a] dark:text-white leading-tight mb-4 uppercase">
                        Personalized Health Recommendations
                    </h2>
                    <p className="text-lg text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                        Based on your latest biometrics, genetic markers, and lifestyle data, our AI has
                        formulated these high-impact adjustments to optimize your long-term longevity and
                        prevent chronic conditions.
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
                    {/* Lifestyle Improvements */}
                    <section className="space-y-6">
                        <div className="flex items-center gap-2 mb-2">
                            <Sparkles size={20} className="text-[#6143f4] animate-pulse" />
                            <h3 className="text-xl font-bold uppercase tracking-tight">Lifestyle Improvements</h3>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            {lifestyleImprovements.map((item) => {
                                const Icon = item.icon;
                                return (
                                    <div
                                        key={item.title}
                                        className="bg-white dark:bg-[#1a1433] rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-white/5 hover:translate-y-[-4px] hover:shadow-xl transition-all duration-300 group"
                                    >
                                        <div
                                            className={`size-12 rounded-xl ${item.bgColor} ${item.color} flex items-center justify-center mb-5 shadow-inner transition-transform group-hover:scale-110`}
                                        >
                                            <Icon size={24} />
                                        </div>
                                        <h4 className="font-black text-lg mb-1 text-[#13082a] dark:text-white uppercase tracking-tight">
                                            {item.title}
                                        </h4>
                                        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed font-bold italic opacity-80">
                                            {item.description}
                                        </p>
                                    </div>
                                );
                            })}

                            {/* AQI Monitor Card */}
                            <div
                                onClick={() => navigate(ROUTES.AQI_MONITOR)}
                                className="bg-gradient-to-br from-[#13082a] to-[#0c091a] rounded-2xl p-6 shadow-xl border border-[#6143f4]/30 hover:translate-y-[-4px] transition-all duration-300 group cursor-pointer relative overflow-hidden"
                            >
                                <div className="absolute -right-4 -top-4 opacity-10 group-hover:rotate-12 transition-transform duration-700">
                                    <Wind size={80} className="text-white" />
                                </div>
                                <div className="size-12 rounded-xl bg-[#6143f4]/20 text-[#6143f4] flex items-center justify-center mb-5 shadow-lg border border-[#6143f4]/30">
                                    <Wind size={24} className="animate-pulse" />
                                </div>
                                <h4 className="font-black text-lg mb-1 text-white uppercase tracking-tight">
                                    Environmental Risk
                                </h4>
                                <p className="text-xs text-white/50 leading-relaxed font-bold italic mb-4">
                                    Current AQI: <span className="text-[#6143f4]">Unhealthy</span>. Avoid outdoor
                                    cardio.
                                </p>
                                <span className="text-[10px] font-black uppercase tracking-widest text-[#6143f4] flex items-center gap-1">
                                    Check Air Quality <ArrowRight size={12} />
                                </span>
                            </div>
                        </div>
                    </section>

                    {/* Dietary Optimization */}
                    <section className="space-y-6">
                        <div className="flex items-center gap-2 mb-2">
                            <Utensils size={20} className="text-[#009cde]" />
                            <h3 className="text-xl font-bold uppercase tracking-tight">Dietary Optimization</h3>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                            {dietaryOptimization.map((item) => (
                                <div
                                    key={item.title}
                                    className={`bg-white dark:bg-[#1a1433] rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-white/5 hover:translate-y-[-4px] hover:shadow-xl transition-all duration-300 ${item.borderColor}`}
                                >
                                    <h4 className="font-black mb-1 text-[#13082a] dark:text-white uppercase tracking-tight text-sm">
                                        {item.title}
                                    </h4>
                                    <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed font-bold opacity-80 mb-5">
                                        {item.description}
                                    </p>
                                    <span
                                        className={`text-[10px] font-black uppercase tracking-widest ${item.priorityColor} px-2.5 py-1 rounded-full shadow-sm`}
                                    >
                                        {item.priority}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Fitness & Activity */}
                    <section className="space-y-6">
                        <div className="flex items-center gap-2 mb-2">
                            <Dumbbell size={20} className="text-orange-500" />
                            <h3 className="text-xl font-bold uppercase tracking-tight">Fitness & Activity</h3>
                        </div>
                        <div className="bg-white dark:bg-[#1a1433] rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-800 transition-all duration-300 group relative overflow-hidden">
                            <div className="flex flex-col sm:flex-row items-start justify-between gap-6 relative z-10">
                                <div className="flex-1">
                                    <h4 className="font-black text-xl mb-3 text-[#13082a] dark:text-white tracking-tight uppercase leading-none">
                                        Zone 2 Cardiovascular Training
                                    </h4>
                                    <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-6 font-medium">
                                        Aim for 150 minutes per week at a heart rate of 125-135 BPM. This will improve
                                        mitochondrial density and metabolic flexibility.
                                    </p>
                                    <div className="flex gap-2">
                                        <div className="px-3.5 py-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs font-black uppercase tracking-widest leading-none">
                                            3x / Week
                                        </div>
                                        <div className="px-3.5 py-1.5 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs font-black uppercase tracking-widest leading-none">
                                            50 min sessions
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </section>

                    {/* Sleep Optimization */}
                    <section className="space-y-6">
                        <div className="flex items-center gap-2 mb-2">
                            <Moon size={20} className="text-indigo-500" />
                            <h3 className="text-xl font-bold uppercase tracking-tight">Sleep Optimization</h3>
                        </div>
                        <div className="bg-gradient-to-br from-indigo-600 to-indigo-800 rounded-2xl p-8 text-white shadow-xl relative overflow-hidden group">
                            <div className="relative z-10">
                                <h4 className="font-black text-xl mb-2 tracking-tight uppercase leading-none">
                                    Digital Detox Routine
                                </h4>
                                <p className="text-indigo-100 text-sm mb-5 font-semibold leading-relaxed">
                                    Eliminate blue light exposure 90 minutes before your target sleep time of 10:30 PM.
                                </p>
                                <ul className="space-y-3">
                                    <li className="flex items-center gap-3 text-xs font-black uppercase tracking-widest bg-white/10 backdrop-blur-md px-4 py-2 rounded-xl border border-white/5 w-fit shadow-md">
                                        <AlarmClock size={16} />
                                        Fixed wake time: 6:30 AM
                                    </li>
                                    <li className="flex items-center gap-3 text-xs font-black uppercase tracking-widest bg-white/10 backdrop-blur-md px-4 py-2 rounded-xl border border-white/5 w-fit shadow-md">
                                        <Thermometer size={16} />
                                        Room temp: 65°F (18°C)
                                    </li>
                                </ul>
                            </div>
                            <Moon
                                size={120}
                                className="absolute -right-8 -bottom-8 text-white/10 rotate-12 group-hover:rotate-0 transition-transform duration-1000"
                                strokeWidth={1}
                            />
                        </div>
                    </section>
                </div>

                {/* Recommended Lab Tests */}
                <section className="mt-12">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-2">
                            <FlaskConical size={24} className="text-[#6143f4]" />
                            <h3 className="text-2xl font-black uppercase tracking-tight">Recommended Lab Tests</h3>
                        </div>
                        <button className="text-[#6143f4] font-black text-sm hover:underline flex items-center gap-1 group">
                            View Full History <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                        </button>
                    </div>
                    <div className="overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#1a1433] shadow-md">
                        <div className="overflow-x-auto">
                            <table className="w-full text-left">
                                <thead className="bg-slate-50 dark:bg-white/5 border-b border-slate-200 dark:border-slate-800">
                                    <tr>
                                        <th className="px-8 py-5 text-sm font-black uppercase tracking-widest text-[#13082a] dark:text-white">
                                            Test Name
                                        </th>
                                        <th className="px-8 py-5 text-sm font-black uppercase tracking-widest text-[#13082a] dark:text-white">
                                            Why it matters
                                        </th>
                                        <th className="px-8 py-5 text-sm font-black uppercase tracking-widest text-[#13082a] dark:text-white">
                                            Suggested Date
                                        </th>
                                        <th className="px-8 py-5 text-sm font-black uppercase tracking-widest text-right text-[#13082a] dark:text-white">
                                            Action
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                    {labTests.map((test) => (
                                        <tr
                                            key={test.name}
                                            className="hover:bg-slate-50/50 dark:hover:bg-white/5 transition-colors group"
                                        >
                                            <td className="px-8 py-6">
                                                <p className="font-bold text-sm text-[#13082a] dark:text-white group-hover:text-[#6143f4] transition-colors">
                                                    {test.name}
                                                </p>
                                                <p className="text-[11px] text-slate-400 font-bold uppercase mt-1 tracking-tighter leading-none">
                                                    {test.category}
                                                </p>
                                            </td>
                                            <td className="px-8 py-6 text-sm text-slate-600 dark:text-slate-400 leading-relaxed max-w-sm italic">
                                                {test.reason}
                                            </td>
                                            <td className="px-8 py-6">
                                                <div className="flex items-center gap-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                                                    <CalendarDays size={16} className="text-slate-400" />
                                                    {test.date}
                                                </div>
                                            </td>
                                            <td className="px-8 py-6 text-right">
                                                <button className="px-5 py-2.5 bg-[#6143f4]/10 text-[#6143f4] text-xs font-black uppercase tracking-widest rounded-xl hover:bg-[#6143f4] hover:text-white transition-all shadow-sm active:scale-95 leading-none">
                                                    Order Kit
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </section>

                {/* Bottom CTA */}
                <section className="mt-12 mb-12">
                    <div className="bg-gradient-to-br from-[#6143f4] to-[#009cde] rounded-3xl p-10 lg:p-14 text-white flex flex-col lg:flex-row items-center justify-between gap-10 shadow-2xl shadow-[#6143f4]/30 relative overflow-hidden group">
                        <div className="relative z-10 max-w-2xl">
                            <h3 className="text-4xl font-black mb-5 tracking-tight leading-none uppercase">
                                Want to dive deeper?
                            </h3>
                            <p className="text-white/80 text-xl font-medium leading-relaxed italic">
                                Schedule a session with an ArogyaAI specialist to review these recommendations and
                                build a clinical roadmap tailored to your genomic data.
                            </p>
                        </div>
                        <div className="relative z-10 flex gap-4 w-full lg:w-auto">
                            <button
                                onClick={() => navigate(ROUTES.HELP)}
                                className="flex-1 lg:flex-none px-10 py-5 bg-white text-[#6143f4] font-black text-xs uppercase tracking-[0.3em] rounded-2xl hover:scale-[1.05] transition-all shadow-2xl active:scale-95 flex items-center justify-center gap-3"
                            >
                                <ArrowRight size={18} />
                                Open Support Center
                            </button>
                        </div>
                        <div className="absolute top-0 right-0 size-80 bg-white/10 rounded-full -mr-20 -mt-20 blur-3xl group-hover:scale-150 transition-transform duration-1000"></div>
                        <div className="absolute bottom-0 left-0 size-64 bg-black/10 rounded-full -ml-20 -mb-20 blur-3xl group-hover:scale-150 transition-transform duration-1000"></div>
                    </div>
                </section>

                {/* Footer */}
                <footer className="mt-20 py-10 border-t border-slate-200 dark:border-slate-800 text-center text-slate-400 dark:text-slate-500 text-sm font-semibold">
                    <p>
                        © 2024 ArogyaAI Preventive Systems. All AI insights are for informational purposes and
                        should be discussed with a healthcare professional.
                    </p>
                </footer>
            </div>
        </div>
    );
};

export default PreventiveRecommendations;

