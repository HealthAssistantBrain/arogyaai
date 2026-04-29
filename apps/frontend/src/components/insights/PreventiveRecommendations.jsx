import React from 'react';
import { motion } from 'framer-motion';
import {
    Activity,
    ArrowDown,
    ArrowRight,
    ArrowUp,
    Brain,
    Dumbbell,
    Lightbulb,
    Moon,
    Rocket,
    ShieldCheck,
    Sparkles,
    Utensils,
    Dna,
    Calendar,
    Ban,
    User
} from 'lucide-react';
import { safeArray } from '../../utils/safeData';

const itemVariants = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } },
};

const containerVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const riskStyles = {
    diabetes: {
        ring: 'border-[#009CDE]/20',
        fill: 'bg-[#009CDE]',
        badge: 'bg-[#009CDE]/10 text-[#009CDE]',
    },
    hypertension: {
        ring: 'border-[#6043F4]/20',
        fill: 'bg-[#6043F4]',
        badge: 'bg-[#6043F4]/10 text-[#6043F4]',
    },
    cad: {
        ring: 'border-[#13082A]/15',
        fill: 'bg-[#13082A]',
        badge: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
    },
};

const levelStyles = {
    LOW: 'bg-green-100 text-green-600 dark:bg-green-500/10 dark:text-green-400',
    MODERATE: 'bg-amber-100 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300',
    HIGH: 'bg-rose-100 text-rose-700 dark:bg-rose-500/10 dark:text-rose-300',
    CRITICAL: 'bg-red-100 text-red-700 dark:bg-red-500/10 dark:text-red-300',
};

const PreventiveRecommendations = ({ data }) => {
    const { risks, shap, summary, recommendations, sources, labResults } = data;

    const groupedRecommendations = safeArray(recommendations).reduce((acc, rec) => {
        const cat = rec.category?.toLowerCase() || 'lifestyle';
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(rec);
        return acc;
    }, {});

    return (
        <div className="space-y-12">
            {/* Header Section */}
            <div className="mb-10">
                <h2 className="text-4xl font-black tracking-tight mb-4 dark:text-white">Personalized Health Recommendations</h2>
                <div className="bg-[#6043F4] p-8 rounded-xl text-white shadow-xl shadow-[#6043F4]/20 relative overflow-hidden group mb-8">
                    <div className="relative z-10">
                        <Lightbulb size={40} className="mb-4 text-white hover:rotate-12 transition-transform duration-500" />
                        <h3 className="text-lg font-bold mb-3 tracking-tight">Deep Analysis</h3>
                        <p className="text-lg text-white font-medium leading-relaxed max-w-4xl">
                            {summary || "Based on your latest biometrics, genetic markers, and lifestyle data, our AI has formulated these high-impact adjustments to optimize your long-term longevity and prevent chronic conditions."}
                        </p>
                        {safeArray(sources).length > 0 ? (
                            <div className="mt-4 flex flex-wrap gap-2">
                                {safeArray(sources).slice(0, 3).map((source) => (
                                    <span
                                        key={`${source.source}-${source.chunk_id}`}
                                        className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-white/80"
                                    >
                                        {source.source}
                                    </span>
                                ))}
                            </div>
                        ) : null}
                    </div>
                    <div className="absolute -bottom-10 -right-10 size-64 bg-white/10 rounded-full blur-3xl group-hover:scale-150 transition-transform duration-1000" />
                </div>
            </div>

            {/* Risk Cards Section */}
            <div className="space-y-6">
                <h3 className="text-2xl font-bold dark:text-white flex items-center gap-2">
                    <ShieldCheck className="text-primary" /> Multi-Condition Risk Analysis
                </h3>
                <motion.div variants={containerVariants} initial="initial" animate="animate" className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {safeArray(risks).map((risk) => {
                        const theme = riskStyles[risk.key] || riskStyles.cad;
                        const levelClass = levelStyles[risk.riskLevel] || levelStyles.LOW;
                        const trendIcon = risk.deltaFromNeutral >= 0 ? <ArrowUp size={12} /> : <ArrowDown size={12} />;

                        return (
                            <motion.div
                                key={risk.key}
                                variants={itemVariants}
                                className={`bg-white dark:bg-slate-900/50 p-6 rounded-xl border shadow-sm hover:border-[#6043F4]/20 transition-all cursor-pointer group ${theme.ring}`}
                            >
                                <div className="flex justify-between items-start mb-4">
                                    <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">{risk.title}</p>
                                    <span className={`${levelClass} text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider`}>
                                        {risk.status}
                                    </span>
                                </div>
                                <div className="flex items-baseline gap-2 mb-4">
                                    <span className="text-3xl font-bold text-[#13082A] dark:text-white">{risk.value.toFixed(1)}%</span>
                                    <span className={`text-xs font-bold flex items-center gap-0.5 ${risk.deltaFromNeutral >= 0 ? 'text-rose-500' : 'text-emerald-500'}`}>
                                        {trendIcon}
                                        {risk.trend}
                                    </span>
                                </div>
                                <div className="h-10 w-full bg-gradient-to-r from-[#009CDE]/10 to-[#6043F4]/10 rounded flex items-center px-1">
                                    <div className="h-1 w-full bg-slate-200 dark:bg-slate-800 rounded-full relative overflow-hidden">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${risk.progress}%` }}
                                            transition={{ duration: 1, ease: 'easeOut' }}
                                            className={`h-full ${theme.fill} rounded-full`}
                                        />
                                    </div>
                                </div>
                            </motion.div>
                        );
                    })}
                </motion.div>
            </div>

            {/* Grid of Recommendations */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Lifestyle Improvements */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                        <Sparkles className="text-primary" size={24} />
                        <h3 className="text-xl font-bold dark:text-white">Lifestyle Improvements</h3>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {groupedRecommendations.lifestyle ? groupedRecommendations.lifestyle.map((rec, i) => (
                            <div key={i} className="glass-card bg-white dark:bg-slate-900/40 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
                                <div className="size-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center mb-4">
                                    <User size={24} />
                                </div>
                                <h4 className="font-bold mb-1 dark:text-white">{rec.title}</h4>
                                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{rec.detail}</p>
                            </div>
                        )) : (
                            <div className="glass-card bg-white dark:bg-slate-900/40 rounded-xl p-5 shadow-sm text-center col-span-2">
                                <p className="text-sm text-slate-400">Maintain current wellness practices.</p>
                            </div>
                        )}
                    </div>
                </section>

                {/* Dietary Optimization */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                        <Utensils className="text-secondary" size={24} />
                        <h3 className="text-xl font-bold dark:text-white">Dietary Optimization</h3>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {groupedRecommendations.metabolic ? groupedRecommendations.metabolic.map((rec, i) => (
                            <div key={i} className="glass-card bg-white dark:bg-slate-900/40 rounded-xl p-5 shadow-sm border-l-4 border-secondary">
                                <h4 className="font-bold mb-1 text-sm dark:text-white">{rec.title}</h4>
                                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed mb-3">{rec.detail}</p>
                                <span className="text-[10px] font-bold text-secondary uppercase tracking-tighter bg-secondary/10 px-2 py-0.5 rounded">High Priority</span>
                            </div>
                        )) : (
                            <div className="glass-card bg-white dark:bg-slate-900/40 rounded-xl p-5 shadow-sm text-center col-span-2">
                                <p className="text-sm text-slate-400">Continue your balanced nutrition plan.</p>
                            </div>
                        )}
                    </div>
                </section>

                {/* Fitness & Activity */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                        <Dumbbell className="text-orange-500" size={24} />
                        <h3 className="text-xl font-bold dark:text-white">Fitness & Activity</h3>
                    </div>
                    <div className="glass-card bg-white dark:bg-slate-900/40 rounded-xl p-6 shadow-sm border border-slate-200 dark:border-slate-800">
                        {groupedRecommendations.cardiovascular ? groupedRecommendations.cardiovascular.map((rec, i) => (
                            <div key={i} className="flex items-start justify-between gap-4 mb-4 last:mb-0">
                                <div className="flex-1">
                                    <h4 className="font-bold text-lg mb-2 dark:text-white">{rec.title}</h4>
                                    <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed mb-4">{rec.detail}</p>
                                </div>
                            </div>
                        )) : (
                            <p className="text-sm text-slate-400">Maintain current activity levels.</p>
                        )}
                        <div className="flex gap-2">
                            <div className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs font-medium dark:text-slate-300">3x / Week</div>
                            <div className="px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-lg text-xs font-medium dark:text-slate-300">Target BPM: 125-135</div>
                        </div>
                    </div>
                </section>

                {/* Sleep Optimization */}
                <section className="space-y-4">
                    <div className="flex items-center gap-2 mb-2">
                        <Moon className="text-indigo-500" size={24} />
                        <h3 className="text-xl font-bold dark:text-white">Sleep Optimization</h3>
                    </div>
                    <div className="bg-indigo-600 rounded-xl p-6 text-white shadow-lg relative overflow-hidden">
                        <div className="relative z-10">
                            {groupedRecommendations.sleep ? groupedRecommendations.sleep.map((rec, i) => (
                                <div key={i} className="mb-4">
                                    <h4 className="font-bold text-lg mb-2">{rec.title}</h4>
                                    <p className="text-indigo-100 text-sm mb-4">{rec.detail}</p>
                                </div>
                            )) : (
                                <>
                                    <h4 className="font-bold text-lg mb-2">Optimized Rest</h4>
                                    <p className="text-indigo-100 text-sm mb-4">Your current sleep hygiene is excellent. Continue maintaining regular sleep/wake cycles.</p>
                                </>
                            )}
                            <ul className="space-y-2">
                                <li className="flex items-center gap-2 text-xs">
                                    <Activity size={14} /> Fixed wake time: 6:30 AM
                                </li>
                                <li className="flex items-center gap-2 text-xs">
                                    <Activity size={14} /> Recovery Focus: HRV Monitoring
                                </li>
                            </ul>
                        </div>
                        <Moon className="absolute -right-4 -bottom-4 size-32 text-white/10 rotate-12" />
                    </div>
                </section>
            </div>

            {/* SHAP Impact Section (Risk Drivers) */}
            <div className="bg-white dark:bg-slate-900/50 p-8 rounded-xl border border-white dark:border-white/5 shadow-sm">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
                    <div>
                        <h3 className="text-lg font-bold text-[#13082A] dark:text-white">Risk Drivers (SHAP Impact)</h3>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Biometric factors influencing your current risk score</p>
                    </div>
                    <div className="flex gap-4 text-[10px] font-bold uppercase tracking-wider">
                        <div className="flex items-center gap-1.5">
                            <span className="size-2 bg-[#009CDE] rounded-full" /> Decreasing Risk
                        </div>
                        <div className="flex items-center gap-1.5">
                            <span className="size-2 bg-[#6043F4] rounded-full" /> Increasing Risk
                        </div>
                    </div>
                </div>

                <div className="space-y-6">
                    {safeArray(shap).length > 0 ? (
                        safeArray(shap).map((driver, index) => (
                            <div key={driver.key || driver.label} className="relative group/bar">
                                <div className="flex justify-between mb-1 text-sm font-bold tracking-tight">
                                    <span className="text-slate-700 dark:text-slate-300">{driver.label}</span>
                                    <span className={driver.direction === 'increasing' ? 'text-[#6043F4]' : 'text-[#009CDE]'}>{driver.impact}</span>
                                </div>
                                <div className="h-3 w-full bg-slate-100 dark:bg-slate-800 rounded-full flex justify-center items-center relative overflow-hidden shadow-inner">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: driver.barWidth }}
                                        transition={{ duration: 1, delay: index * 0.08 }}
                                        className={`absolute ${driver.direction === 'increasing' ? 'left-1/2 rounded-r-full' : 'right-1/2 rounded-l-full'} h-full ${driver.direction === 'increasing' ? 'bg-[#6043F4]' : 'bg-[#009CDE]'
                                            } shadow-sm`}
                                    />
                                    <div className="absolute left-1/2 top-0 h-full w-[1px] bg-slate-300 dark:bg-slate-700 z-10" />
                                </div>
                            </div>
                        ))
                    ) : (
                        <p className="text-sm text-slate-500 dark:text-slate-400">No driver data available</p>
                    )}
                </div>
            </div>

            {/* Lab Tests Section */}
            <section className="mt-12">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-2">
                        <Dna className="text-primary" size={24} />
                        <h3 className="text-2xl font-bold dark:text-white">Recommended Lab Tests</h3>
                    </div>
                    <button className="text-primary font-bold text-sm hover:underline flex items-center gap-1">
                        View All Lab History <ArrowRight size={16} />
                    </button>
                </div>
                <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 dark:bg-slate-800/50">
                            <tr>
                                <th className="px-6 py-4 text-sm font-bold dark:text-slate-200">Test Name</th>
                                <th className="px-6 py-4 text-sm font-bold dark:text-slate-200">Why it matters</th>
                                <th className="px-6 py-4 text-sm font-bold dark:text-slate-200">Suggested Date</th>
                                <th className="px-6 py-4 text-sm font-bold text-right dark:text-slate-200">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {safeArray(labResults).length > 0 ? labResults.slice(0, 3).map((test, i) => (
                                <tr key={i}>
                                    <td className="px-6 py-5">
                                        <p className="font-bold text-sm dark:text-white">{test.name || test.title}</p>
                                        <p className="text-xs text-slate-400">{test.category || "Health Marker"}</p>
                                    </td>
                                    <td className="px-6 py-5 text-sm text-slate-600 dark:text-slate-400">{test.description || "To monitor specific biomarkers."}</td>
                                    <td className="px-6 py-5 text-sm dark:text-slate-300">{test.date || "Next Quarter"}</td>
                                    <td className="px-6 py-5 text-right">
                                        <button className="px-4 py-2 bg-primary/10 text-primary text-xs font-bold rounded-lg hover:bg-primary/20 transition-colors">Order Kit</button>
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td className="px-6 py-5" colSpan="4">
                                        <p className="text-center text-sm text-slate-400">No pending lab tests recommended</p>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </section>

            {/* CTA Section */}
            <section className="mt-12 mb-12">
                <div className="bg-gradient-to-r from-primary to-secondary rounded-2xl p-8 text-white flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl relative overflow-hidden">
                    <div className="relative z-10">
                        <h3 className="text-3xl font-black mb-2">Want to dive deeper?</h3>
                        <p className="text-white/80 max-w-lg">Schedule a session with an ArogyaAI specialist to review these recommendations and build a clinical roadmap tailored to your genomic data.</p>
                    </div>
                    <div className="relative z-10 flex gap-4 w-full md:w-auto">
                        <button className="flex-1 md:flex-none px-8 py-4 bg-white text-primary font-bold rounded-xl hover:bg-slate-50 transition-colors flex items-center justify-center gap-2">
                            <Calendar size={18} />
                            Book Consultation
                        </button>
                    </div>
                    <div className="absolute top-0 right-0 size-64 bg-white/10 rounded-full -mr-20 -mt-20 blur-3xl" />
                    <div className="absolute bottom-0 left-0 size-48 bg-secondary/20 rounded-full -ml-20 -mb-20 blur-3xl" />
                </div>
            </section>

            {/* Footer */}
            <footer className="mt-20 py-10 border-t border-slate-200 dark:border-slate-800 text-center text-slate-400 text-sm">
                <p>© 2026 ArogyaAI Preventive Systems. All AI insights are for informational purposes and should be discussed with a healthcare professional.</p>
            </footer>
        </div>
    );
};

export default PreventiveRecommendations;
