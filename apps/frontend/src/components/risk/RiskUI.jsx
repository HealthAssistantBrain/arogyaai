import React from 'react';
import { motion } from 'framer-motion';
import {
    Activity,
    TrendingUp,
    ShieldCheck,
    Info,
    History,
    ChevronRight,
    Download,
    TestTube2,
    Zap,
    Scale,
    Dna
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../router/routes';

const RiskUI = ({ riskData, loading, onSimulatorClick }) => {
    const navigate = useNavigate();

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <div className="flex flex-col items-center gap-4">
                    <div className="size-12 border-4 border-[#6143f4] border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-slate-500 font-bold animate-pulse uppercase tracking-widest text-xs">Generating Prediction...</p>
                </div>
            </div>
        );
    }

    const {
        risk_score = 0,
        risk_level = 'Unknown',
        confidence = 0,
        analysis = '',
        drivers = [],
        recommendations = [],
        biological_age_delta = 'N/A',
        last_updated = null
    } = riskData || {};

    const getRiskColor = (level) => {
        const l = level?.toLowerCase();
        if (l === 'high' || l === 'critical') return 'text-red-600 bg-red-100 dark:bg-red-900/30';
        if (l === 'moderate') return 'text-orange-600 bg-orange-100 dark:bg-orange-900/30';
        return 'text-green-600 bg-green-100 dark:bg-green-900/30';
    };

    const getIndicatorColor = (level) => {
        const l = level?.toLowerCase();
        if (l === 'high' || l === 'critical') return 'bg-red-600';
        if (l === 'moderate') return 'bg-orange-600';
        return 'bg-green-600';
    };



    return (
        <div className="max-w-6xl mx-auto space-y-10">
            {/* Header & Actions Section */}
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 font-display">
                <div>
                    <nav className="flex items-center gap-2 text-xs font-bold text-[#6143f4] mb-2 uppercase tracking-tighter">
                        <span className="cursor-pointer hover:underline" onClick={() => navigate(ROUTES.DASHBOARD)}>Analysis</span>
                        <ChevronRight size={14} className="text-slate-400" />
                        <span className="text-slate-500">Risk Explanation</span>
                    </nav>
                    <h2 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tight leading-none uppercase">Condition Risk Assessment</h2>
                    <p className="text-slate-500 mt-2 font-bold flex items-center gap-2">
                        Last Updated: <span className="font-mono text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
                            {last_updated ? new Date(last_updated).toLocaleString() : 'Never'}
                        </span>
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <button className="px-5 py-3 bg-white dark:bg-[#1C1136] border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-bold text-[#13082a] dark:text-white shadow-sm hover:bg-slate-50 transition-all flex items-center gap-2 active:scale-95">
                        <Download size={18} />
                        Export Report
                    </button>
                    <button
                        onClick={onSimulatorClick}
                        className="px-5 py-3 bg-[#6143f4] text-white rounded-xl text-sm font-bold shadow-lg shadow-[#6143f4]/25 hover:bg-[#6143f4]/90 transition-all flex items-center gap-2 active:scale-95"
                    >
                        <TestTube2 size={18} />
                        Open Disease Simulator
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-12 gap-6 pb-12 font-display">
                {/* Risk Level Gauge Card */}
                <div className="col-span-12 lg:col-span-4 bg-white dark:bg-[#1a1433] rounded-3xl p-8 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col items-center justify-center relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-30 cursor-pointer">
                        <Info size={20} className="text-slate-300 group-hover:text-[#6143f4] transition-colors" />
                    </div>
                    <div className="relative size-48">
                        <svg className="size-full transform -rotate-90" viewBox="0 0 100 100">
                            <circle className="text-slate-100 dark:text-slate-800" cx="50" cy="50" fill="transparent" r="45" stroke="currentColor" strokeWidth="8"></circle>
                            <motion.circle
                                initial={{ strokeDashoffset: 282.7 }}
                                animate={{ strokeDashoffset: 282.7 - (282.7 * risk_score / 100) }}
                                transition={{ duration: 1.5, ease: "easeOut" }}
                                className="text-[#6143f4]"
                                cx="50"
                                cy="50"
                                fill="transparent"
                                r="45"
                                stroke="currentColor"
                                strokeDasharray="282.7"
                                strokeLinecap="round"
                                strokeWidth="8"
                            ></motion.circle>
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <span className="text-5xl font-black text-[#13082a] dark:text-white leading-none">{Math.round(risk_score)}%</span>
                            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mt-1">Risk Level</span>
                        </div>
                    </div>
                    <div className="mt-8 text-center px-4">
                        <div className={`inline-flex items-center gap-2 px-3 py-1 ${getRiskColor(risk_level)} rounded-full text-xs font-bold mb-3 uppercase tracking-wider leading-none`}>
                            <span className={`size-2 ${getIndicatorColor(risk_level)} rounded-full animate-pulse shadow-sm`}></span>
                            {risk_level} Risk
                        </div>
                        <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed font-semibold italic">
                            {analysis || "Data analysis is currently in progress. Your risk is calculated based on longitudinal trends and biometric benchmarks."}
                        </p>
                    </div>
                </div>

                {/* Prediction Explanation Panel */}
                <div className="col-span-12 lg:col-span-8 bg-white dark:bg-[#1a1433] rounded-3xl p-8 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col group">
                    <div className="flex items-center justify-between mb-8">
                        <h3 className="text-xl font-bold text-[#13082a] dark:text-white uppercase flex items-center gap-2">
                            <TrendingUp size={22} className="text-[#6143f4]" />
                            Prediction Explanation
                        </h3>
                        {confidence > 0 && (
                            <div className="flex items-center gap-2 text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 px-3 py-1.5 rounded-lg border border-green-100 dark:border-green-800/50 shadow-sm">
                                <ShieldCheck size={18} />
                                <span className="text-[11px] font-bold leading-none">{Math.round(confidence * 100)}% Prediction Confidence</span>
                            </div>
                        )}
                    </div>
                    <div className="space-y-6">
                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed text-lg font-medium">
                            The <span className="font-bold text-[#13082a] dark:text-white border-b-2 border-[#6143f4]/30">ArogyaAI Engine</span> has analyzed your health trajectory.
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 pt-2">
                            <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-100 dark:border-white/5 transition-colors hover:bg-[#6143f4]/5">
                                <p className="text-[10px] font-black text-slate-400 uppercase mb-2 tracking-widest leading-none">Biological Age</p>
                                <p className="text-sm font-black text-[#13082a] dark:text-white leading-none">{biological_age_delta}</p>
                            </div>
                            <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-100 dark:border-white/5 transition-colors hover:bg-[#6143f4]/5">
                                <p className="text-[10px] font-black text-slate-400 uppercase mb-2 tracking-widest leading-none">Primary Driver</p>
                                <p className="text-sm font-black text-[#13082a] dark:text-white leading-none">
                                    {drivers[0]?.label || 'Metabolic Trends'}
                                </p>
                            </div>
                            <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-100 dark:border-white/5 transition-colors hover:bg-[#6143f4]/5">
                                <p className="text-[10px] font-black text-slate-400 uppercase mb-2 tracking-widest leading-none">Action Priority</p>
                                <p className="text-sm font-black text-[#13082a] dark:text-white leading-none">High</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* SHAP Feature Analysis Section */}
                <div className="col-span-12 lg:col-span-8 bg-white dark:bg-[#1a1433] rounded-3xl p-8 shadow-sm border border-slate-200 dark:border-slate-800">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
                        <div>
                            <h3 className="text-xl font-bold text-[#13082a] dark:text-white uppercase leading-none">SHAP Feature Importance</h3>
                            <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 font-medium">Contribution of each biomarker to the total risk score</p>
                        </div>
                        <div className="flex items-center gap-4 text-[11px] font-bold uppercase tracking-tight">
                            <div className="flex items-center gap-1.5 text-slate-500">
                                <span className="size-2 rounded-full bg-[#6143f4] shadow-sm shadow-[#6143f4]/30"></span>
                                Increases Risk
                            </div>
                            <div className="flex items-center gap-1.5 text-slate-500">
                                <span className="size-2 rounded-full bg-[#009cde] shadow-sm shadow-[#009cde]/30"></span>
                                Decreases Risk
                            </div>
                        </div>
                    </div>
                    <div className="space-y-7">
                        {drivers.length > 0 ? drivers.map((driver) => (
                            <div key={driver.key || driver.label} className="relative group cursor-help">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-bold text-[#13082a] dark:text-white group-hover:text-[#6143f4] transition-colors">{driver.label}</span>
                                    <span className={`text-sm font-black ${driver.direction === 'decreasing' ? 'text-[#009cde]' : 'text-[#6143f4]'}`}>
                                        {driver.impact}
                                    </span>
                                </div>
                                <div className={`h-3 w-full bg-slate-100 dark:bg-slate-800/50 rounded-full overflow-hidden flex ${driver.direction === 'decreasing' ? 'flex-row-reverse' : ''} shadow-inner`}>
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${Math.min(100, Math.abs(driver.contribution) * 2)}%` }}
                                        transition={{ duration: 1.2, ease: "easeOut" }}
                                        className={`h-full ${driver.direction === 'decreasing' ? 'bg-[#009cde]' : 'bg-[#6143f4]'} rounded-full shadow-sm`}
                                    ></motion.div>
                                </div>
                            </div>
                        )) : (
                            <p className="text-slate-500 italic text-center py-4">No detailed drivers available yet.</p>
                        )}
                    </div>
                </div>

                {/* Contributing Factors List Section */}
                <div className="col-span-12 lg:col-span-4 bg-white dark:bg-[#1a1433] rounded-3xl p-8 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col group">
                    <h3 className="text-xl font-bold text-[#13082a] dark:text-white mb-6 uppercase leading-none">Recommendations</h3>
                    <div className="space-y-4 flex-1">
                        {recommendations.length > 0 ? recommendations.map((rec, i) => {
                            const title = typeof rec === 'string' ? rec : rec.title;
                            return (
                                <div key={i} className={`p-4 rounded-2xl border bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/5 flex flex-col gap-2 transition-transform hover:scale-[1.02] active:scale-[0.98] group/factor shadow-sm hover:shadow-md`}>
                                    <div className="flex items-center gap-3">
                                        <div className="size-8 bg-white dark:bg-slate-800 rounded-lg flex items-center justify-center shadow-sm group-hover/factor:rotate-12 transition-transform">
                                            <Zap size={16} className="text-[#6143f4]" />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-sm font-bold text-[#13082a] dark:text-white leading-tight">{title}</p>
                                        </div>
                                    </div>
                                    {rec.detail && <p className="text-xs text-slate-500 dark:text-slate-400">{rec.detail}</p>}
                                </div>
                            );
                        }) : (
                            <p className="text-slate-500 italic text-center py-4">Generating personalized recommendations...</p>
                        )}
                    </div>
                    <button className="w-full mt-8 py-3.5 bg-slate-900 dark:bg-[#6143f4] text-white rounded-xl text-sm font-bold hover:shadow-lg transition-all flex items-center justify-center gap-2 active:scale-95 group-hover:bg-slate-800 dark:group-hover:bg-[#6143f4]/90" onClick={() => navigate(ROUTES.TIMELINE)}>
                        <History size={18} />
                        View Historical Trend
                    </button>
                </div>
            </div>
        </div>
    );
};

export default RiskUI;
