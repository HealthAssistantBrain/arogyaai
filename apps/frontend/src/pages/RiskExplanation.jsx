import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  LayoutDashboard, 
  Activity, 
  Brain, 
  FlaskConical, 
  Calendar, 
  Settings, 
  Search, 
  Bell, 
  MessageSquare,
  ChevronRight,
  Download,
  TestTube2,
  Info,
  ShieldCheck,
  TrendingUp,
  History,
  Dna,
  Scale,
  Zap
} from 'lucide-react';
import { ROUTES } from '../router/routes';
import { openCommandPalette } from '../components/CommandPalette';

const RiskExplanation = () => {
    const navigate = useNavigate();

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
        { icon: Activity, label: 'Health Risks', path: ROUTES.RISK_EXPLANATION, active: true },
        { icon: Brain, label: 'Disease Simulator', path: ROUTES.SIMULATOR },
        { icon: FlaskConical, label: 'Lab Results', path: ROUTES.LAB_RESULTS },
        { icon: Calendar, label: 'Health Timeline', path: ROUTES.TIMELINE },
    ];

    const shapFeatures = [
        { label: 'Blood Sugar (HbA1c)', impact: '+22.4%', width: '75%', color: 'bg-[#6143f4]', shadow: 'shadow-[0_0_8px_rgba(97,67,244,0.4)]' },
        { label: 'Body Mass Index (BMI)', impact: '+15.8%', width: '55%', color: 'bg-[#6143f4]/80', shadow: '' },
        { label: 'Physical Activity Level', impact: '+12.1%', width: '42%', color: 'bg-[#6143f4]/60', shadow: '' },
        { label: 'HDL Cholesterol', impact: '-8.4%', width: '25%', color: 'bg-[#009cde]', shadow: 'shadow-[0_0_8px_rgba(0,156,222,0.4)]', negative: true },
    ];

    const factors = [
        { icon: Zap, label: 'Glucose', status: 'Critical Elevation', value: '142 mg/dL', bgColor: 'bg-red-50', textColor: 'text-red-600', borderColor: 'border-red-100', iconColor: 'text-red-600' },
        { icon: Scale, label: 'BMI', status: 'Overweight', value: '29.4', bgColor: 'bg-orange-50', textColor: 'text-orange-600', borderColor: 'border-orange-100', iconColor: 'text-orange-600' },
        { icon: Activity, label: 'Resting HR', status: 'Optimal Range', value: '68 BPM', bgColor: 'bg-blue-50', textColor: 'text-blue-600', borderColor: 'border-blue-100', iconColor: 'text-blue-600' },
        { icon: Dna, label: 'Genetics', status: 'Moderate Load', value: 'Tier 2', bgColor: 'bg-purple-50', textColor: 'text-purple-600', borderColor: 'border-purple-100', iconColor: 'text-purple-600' },
    ];

    return (
        <div className="bg-[#eaeaea] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex overflow-hidden antialiased">
            
            {/* Sidebar Navigation - Matched Stitch */}


            {/* Main Content Area */}
            <main className="flex-1 flex flex-col overflow-hidden">
                
                {/* Top Header Navbar - Matched Stitch */}
                <header className="h-20 bg-white/80 dark:bg-[#1C1136]/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-8 z-30 shrink-0">
                    <div className="flex-1 max-w-xl">
                        <div className="relative group">
                            <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                            <input 
                                className="w-full pl-11 pr-4 py-2.5 bg-slate-100 dark:bg-white/5 border-transparent focus:border-[#6143f4] focus:ring-0 rounded-xl text-sm transition-all outline-none font-medium text-[#13082a] dark:text-white" 
                                placeholder="Search patient ID or biomarker..." 
                                type="text"
                            />
                        </div>
                    </div>
                    
                    <div className="flex items-center gap-4">
                        <button className="size-10 flex items-center justify-center rounded-xl hover:bg-slate-100 dark:hover:bg-white/5 text-slate-600 dark:text-slate-400 relative active:scale-95 transition-all" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                            <Bell size={20} />
                            <span className="absolute top-2.5 right-2.5 size-2 bg-red-500 rounded-full border-2 border-white dark:border-[#1C1136]"></span>
                        </button>
                        <button className="size-10 flex items-center justify-center rounded-xl hover:bg-slate-100 dark:hover:bg-white/5 text-slate-600 dark:text-slate-400 active:scale-95 transition-all">
                            <MessageSquare size={20} />
                        </button>
                        <div className="h-8 w-[1px] bg-slate-200 dark:bg-slate-700 mx-2"></div>
                        <div className="flex items-center gap-3 pl-2 cursor-pointer group" onClick={() => navigate(ROUTES.PROFILE)}>
                            <div className="text-right hidden sm:block">
                                <p className="text-sm font-black text-[#13082a] dark:text-white leading-none group-hover:text-[#6143f4] transition-colors">Dr. Aris Thorne</p>
                                <p className="text-[11px] text-slate-500 dark:text-slate-400 font-bold mt-1 leading-none uppercase tracking-tighter">Chief Pathologist</p>
                            </div>
                            <div className="size-10 rounded-full border-2 border-[#6143f4]/20 overflow-hidden shadow-md group-hover:scale-110 transition-transform">
                                <img 
                                    className="w-full h-full object-cover" 
                                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuCAjYte-lVmQqCaOQG_Lm2VoOSNYvpP8ixR2sqMz0Xo5YGEgpYytv5tlq-zawnLNkmofB74hjqVntb49OlJx5eYbjuemo4LAqc93339sH1nGXLNhuNdUN52qJDVC6s6deVIsO8eO_qe-5ksC_BXdekzDZtt0yXtbkaWXxkdy6U6waSHkFbMobKEVQQYOgjepqEJDranLOoYAXyMsgdwOrMYHRUdH_jIKKoxj8r92HPaxVOxowFQ0HAiZ1QIIXMG2ZN-GVLnl5a1XYit" 
                                    alt="Doctor Profile" 
                                />
                            </div>
                        </div>
                    </div>
                </header>

                <div className="flex-1 overflow-y-auto p-8 custom-scrollbar bg-slate-50/30 dark:bg-transparent">
                    <div className="max-w-6xl mx-auto space-y-10">
                        
                        {/* Header & Actions Section */}
                        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                            <div>
                                <nav className="flex items-center gap-2 text-xs font-bold text-[#6143f4] mb-2 uppercase tracking-tighter">
                                    <span className="cursor-pointer hover:underline" onClick={() => navigate(ROUTES.DASHBOARD)}>Analysis</span>
                                    <ChevronRight size={14} className="text-slate-400" />
                                    <span className="text-slate-500">Risk Explanation</span>
                                </nav>
                                <h2 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tight leading-none uppercase">Diabetes Risk Assessment</h2>
                                <p className="text-slate-500 mt-2 font-bold flex items-center gap-2">
                                    Patient ID: <span className="font-mono text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">#AI-88291-ZX</span>
                                </p>
                            </div>
                            <div className="flex items-center gap-3">
                                <button className="px-5 py-3 bg-white dark:bg-[#1C1136] border border-slate-200 dark:border-slate-800 rounded-xl text-sm font-bold text-[#13082a] dark:text-white shadow-sm hover:bg-slate-50 transition-all flex items-center gap-2 active:scale-95">
                                    <Download size={18} />
                                    Export Report
                                </button>
                                <button 
                                    onClick={() => navigate(ROUTES.SIMULATOR)}
                                    className="px-5 py-3 bg-[#6143f4] text-white rounded-xl text-sm font-bold shadow-lg shadow-[#6143f4]/25 hover:bg-[#6143f4]/90 transition-all flex items-center gap-2 active:scale-95"
                                >
                                    <TestTube2 size={18} />
                                    Open Disease Simulator
                                </button>
                            </div>
                        </div>

                        <div className="grid grid-cols-12 gap-6 pb-12">
                            
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
                                            animate={{ strokeDashoffset: 90.5 }}
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
                                        <span className="text-5xl font-black text-[#13082a] dark:text-white leading-none">68%</span>
                                        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mt-1">Risk Level</span>
                                    </div>
                                </div>
                                <div className="mt-8 text-center px-4">
                                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-full text-xs font-bold mb-3 uppercase tracking-wider leading-none">
                                        <span className="size-2 bg-red-600 rounded-full animate-pulse shadow-sm shadow-red-500/50"></span>
                                        High Risk
                                    </div>
                                    <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed font-semibold italic">
                                        "Based on current metabolic trends and genetic markers, the patient shows a high likelihood of Type 2 Diabetes onset within 18 months."
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
                                    <div className="flex items-center gap-2 text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20 px-3 py-1.5 rounded-lg border border-green-100 dark:border-green-800/50 shadow-sm">
                                        <ShieldCheck size={18} />
                                        <span className="text-[11px] font-bold leading-none">94% Prediction Confidence</span>
                                    </div>
                                </div>
                                <div className="space-y-6">
                                    <p className="text-slate-600 dark:text-slate-300 leading-relaxed text-lg font-medium">
                                        The <span className="font-bold text-[#13082a] dark:text-white border-b-2 border-[#6143f4]/30">ArogyaAI Engine</span> has identified a concerning upward trend in fasting blood glucose levels over the last 3 months. This is exacerbated by a <span className="font-bold text-[#6143f4]">sedentary metabolic profile</span> and a BMI of 29.4. 
                                    </p>
                                    <p className="text-slate-600 dark:text-slate-400 leading-relaxed font-semibold opacity-90 border-l-4 border-[#6143f4]/20 pl-4 py-1 italic">
                                        "Key longitudinal data suggests that while genetic predisposition is moderate, the primary drivers are environmental and lifestyle-based. Prediction high confidence rests on consistency across four sessions."
                                    </p>
                                    <div className="grid grid-cols-2 gap-4 mt-4 pt-2">
                                        <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-100 dark:border-white/5 transition-colors hover:bg-[#6143f4]/5">
                                            <p className="text-[10px] font-black text-slate-400 uppercase mb-2 tracking-widest leading-none">Data Source</p>
                                            <p className="text-sm font-black text-[#13082a] dark:text-white leading-none">Longitudinal Clinical Data</p>
                                        </div>
                                        <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/30 border border-slate-100 dark:border-white/5 transition-colors hover:bg-[#6143f4]/5">
                                            <p className="text-[10px] font-black text-slate-400 uppercase mb-2 tracking-widest leading-none">Primary Driver</p>
                                            <p className="text-sm font-black text-[#13082a] dark:text-white leading-none">Metabolic Resistance</p>
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
                                    {shapFeatures.map((feature) => (
                                        <div key={feature.label} className="relative group cursor-help">
                                            <div className="flex items-center justify-between mb-2">
                                                <span className="text-sm font-bold text-[#13082a] dark:text-white group-hover:text-[#6143f4] transition-colors">{feature.label}</span>
                                                <span className={`text-sm font-black ${feature.negative ? 'text-[#009cde]' : 'text-[#6143f4]'}`}>{feature.impact}</span>
                                            </div>
                                            <div className={`h-3 w-full bg-slate-100 dark:bg-slate-800/50 rounded-full overflow-hidden flex ${feature.negative ? 'flex-row-reverse' : ''} shadow-inner`}>
                                                <motion.div 
                                                    initial={{ width: 0 }}
                                                    animate={{ width: feature.width }}
                                                    transition={{ duration: 1.2, ease: "easeOut" }}
                                                    className={`h-full ${feature.color} rounded-full ${feature.shadow}`}
                                                ></motion.div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Contributing Factors List Section */}
                            <div className="col-span-12 lg:col-span-4 bg-white dark:bg-[#1a1433] rounded-3xl p-8 shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col group">
                                <h3 className="text-xl font-bold text-[#13082a] dark:text-white mb-6 uppercase leading-none">Contributing Factors</h3>
                                <div className="space-y-4 flex-1">
                                    {factors.map((factor) => (
                                        <div key={factor.label} className={`${factor.bgColor} dark:bg-white/5 p-4 rounded-2xl border ${factor.borderColor} dark:border-[#6143f4]/10 flex items-center justify-between transition-transform hover:scale-[1.02] active:scale-[0.98] group/factor shadow-sm hover:shadow-md`}>
                                            <div className="flex items-center gap-3">
                                                <div className="size-10 bg-white dark:bg-slate-800 rounded-xl flex items-center justify-center shadow-sm group-hover/factor:rotate-12 transition-transform">
                                                    <factor.icon size={20} className={factor.iconColor} />
                                                </div>
                                                <div>
                                                    <p className="text-sm font-bold text-[#13082a] dark:text-white leading-none">{factor.label}</p>
                                                    <p className={`text-[11px] ${factor.textColor} font-bold mt-1 uppercase tracking-tighter leading-none`}>{factor.status}</p>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <p className="text-sm font-black text-[#13082a] dark:text-white leading-none">{factor.value}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <button className="w-full mt-8 py-3.5 bg-slate-900 dark:bg-[#6143f4] text-white rounded-xl text-sm font-bold hover:shadow-lg transition-all flex items-center justify-center gap-2 active:scale-95 group-hover:bg-slate-800 dark:group-hover:bg-[#6143f4]/90">
                                    <History size={18} />
                                    View Historical Trend
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </main>

            <style dangerouslySetInnerHTML={{ __html: `
                .custom-scrollbar::-webkit-scrollbar { width: 4px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.2); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.4); }
                .font-display { font-family: 'Space Grotesk', sans-serif; }
            `}} />
        </div>
    );
};

export default RiskExplanation;

