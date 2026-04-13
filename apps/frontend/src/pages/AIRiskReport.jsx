import { useNavigate, Link } from 'react-router-dom';
import { 
  LayoutDashboard, 
  ShieldAlert, 
  FileText, 
  FlaskConical, 
  Settings, 
  Search, 
  Bell, 
  HeartPulse, 
  Verified, 
  Fingerprint, 
  Cake, 
  History, 
  Share2, 
  FileDown, 
  TrendingUp, 
  AlertTriangle, 
  Cpu, 
  Brain, 
  Quote, 
  Moon, 
  Dumbbell, 
  Utensils, 
  Lightbulb, 
  ShieldCheck,
  CalendarDays
} from 'lucide-react';
import { ROUTES } from '../router/routes';

const AIRiskReport = () => {
    const navigate = useNavigate();

    const diseases = [
        { name: 'Type 2 Diabetes', status: 'Prediabetic Markers Identified', risk: 'Critical High', riskColor: 'bg-red-100 text-red-700', horizon: '12-18 Months', probability: '74.2%' },
        { name: 'Hypertension', status: 'Fluctuating Systolic Trends', risk: 'Moderate Risk', riskColor: 'bg-amber-100 text-amber-700', horizon: '24-36 Months', probability: '41.8%' },
        { name: 'Cardiovascular Disease', status: 'Stable Lipid Profiles', risk: 'Low Risk', riskColor: 'bg-green-100 text-green-700', horizon: '5+ Years', probability: '12.4%' },
        { name: 'Renal Insufficiency', status: 'Normal eGFR Monitoring', risk: 'Low Risk', riskColor: 'bg-green-100 text-green-700', horizon: '10+ Years', probability: '3.1%' },
    ];

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Overview', path: ROUTES.DASHBOARD },
        { icon: ShieldAlert, label: 'Risk Analysis', path: ROUTES.RISK_EXPLANATION, active: true },
        { icon: FileText, label: 'Records', path: ROUTES.MEDICAL_REPORTS },
        { icon: FlaskConical, label: 'Labs', path: ROUTES.LAB_RESULTS },
        { icon: Settings, label: 'AI Settings', path: ROUTES.SETTINGS },
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col antialiased">
            {/* Top Navigation Bar - Standardized */}
            <header className="sticky top-0 z-50 flex items-center justify-between border-b border-[#6143f4]/10 bg-white/80 dark:bg-[#131022]/80 backdrop-blur-md px-6 py-3 lg:px-12">
                <div className="flex items-center gap-8">
                    <div className="flex items-center gap-3 text-[#6143f4] cursor-pointer group" onClick={() => navigate(ROUTES.DASHBOARD)}>
                        <div className="size-9 bg-[#6143f4] rounded-lg flex items-center justify-center text-white shadow-lg shadow-[#6143f4]/20 transition-transform group-hover:scale-110">
                            <HeartPulse size={20} />
                        </div>
                        <h2 className="text-[#13082a] dark:text-white text-xl font-black tracking-tight leading-none uppercase">ArogyaAI</h2>
                    </div>
                    <div className="hidden md:flex relative h-10 w-64 group">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                        <input className="w-full h-full pl-10 pr-4 rounded-xl border-none bg-slate-100 dark:bg-white/5 focus:ring-2 focus:ring-[#6143f4]/20 text-sm font-medium outline-none transition-all" placeholder="Search records..." type="text"/>
                    </div>
                </div>
                <div className="flex items-center gap-6">
                    <nav className="hidden lg:flex items-center gap-8">
                        <Link to={ROUTES.DASHBOARD} className="text-xs font-black text-[#6143f4] uppercase tracking-widest">Dashboard</Link>
                        <Link to={ROUTES.MEDICAL_REPORTS} className="text-xs font-bold text-slate-500 hover:text-[#6143f4] transition-colors uppercase tracking-widest">Reports</Link>
                        <button className="text-xs font-bold text-slate-500 hover:text-[#6143f4] transition-colors uppercase tracking-widest" type="button">Patients</button>
                        <Link to={ROUTES.INSIGHTS} className="text-xs font-bold text-slate-500 hover:text-[#6143f4] transition-colors uppercase tracking-widest">AI Insights</Link>
                    </nav>
                    <div className="flex items-center gap-3 border-l border-slate-200 dark:border-slate-800 pl-6">
                        <button className="p-2 rounded-xl bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-400 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all active:scale-95 relative" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                            <Bell size={20} />
                            <span className="absolute top-2 right-2 size-2 bg-[#6143f4] rounded-full border-2 border-white dark:border-[#131022]"></span>
                        </button>
                        <div className="size-9 rounded-full bg-[#6143f4]/20 border-2 border-[#6143f4] overflow-hidden cursor-pointer hover:scale-110 transition-transform shadow-md" onClick={() => navigate(ROUTES.SETTINGS)}>
                            <img className="h-full w-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBSNEjoorIjStYduz4toUoH9taRezR9gUmeBlfZqgLvFpq-7Dpa-im_yfn3lhwmaedZOiCg-PEuJeDdpULcssnht9u6CnykpHhZffrOhUXsuZ9iTanq55ms_jcerh6Lq3TN4Or7exJuJ0BaCCElRYRK3NBThOT8RXKoJqVsW5ZC_1R8GCbXb1IaZTElgrP9NB2hNpAClQTc6gsxVwCZJx56bTPuLyvxxphaTbQKe2pAiZg6dxh0LvCzzUm-NNDqI7e0fgO5Z4StDAON" alt="User Profile" />
                        </div>
                    </div>
                </div>
            </header>

            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar Navigation */}


                {/* Main Content Scrollable Area */}
                <main className="flex-1 overflow-y-auto p-6 lg:p-10 custom-scrollbar">
                    <div className="max-w-7xl mx-auto space-y-12 pb-20">
                        
                        {/* Report Header Profile Section */}
                        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-8 mb-12">
                            <div className="flex items-center gap-8">
                                <div className="relative group">
                                    <div className="size-28 lg:size-32 rounded-3xl overflow-hidden ring-4 ring-white dark:ring-slate-800 shadow-2xl group-hover:scale-105 transition-transform duration-500 border border-slate-100 dark:border-slate-800">
                                        <img className="h-full w-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCc4S7BrMst63l1EF95QgKlNEjGLauGZtK-zvEXNiwhaC_HKrzh0fGIN0--r_H5X7KZblLf43XZM-SQJZz6bgXEHpulZaiMCnjrQipOln-UgW9VJdhtL6vztVjadwcmBBd-jqUS95FjW87TYEmluxSQSPMmd-U79Fqmf3l0w4wbog1JtExAELCwKblxOn0h_e2jpZqCRjUbEQH68wJHbEofAX4Y_VrAtkHnou9C-duM3bHlQQf5KZLlhQAoMZjujy35HA0Emub6H6qQ" alt="Alex Johnson Profile" />
                                    </div>
                                    <div className="absolute -bottom-3 -right-3 bg-green-500 text-white size-10 rounded-full flex items-center justify-center border-4 border-white dark:border-slate-800 shadow-xl transition-transform hover:scale-110" title="ArogyaAI Verified">
                                        <Verified size={20} strokeWidth={2.5} />
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    <div className="flex items-center gap-4">
                                        <h1 className="text-4xl lg:text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase leading-none">Alex Johnson</h1>
                                        <span className="px-4 py-1.5 bg-[#6143f4]/10 text-[#6143f4] text-[10px] font-black rounded-full border border-[#6143f4]/20 uppercase tracking-[0.2em] shadow-sm flex items-center gap-2 animate-pulse">
                                            <span className="size-2 bg-[#6143f4] rounded-full"></span>
                                            Verified Profile
                                        </span>
                                    </div>
                                    <div className="flex flex-wrap gap-x-8 gap-y-3 text-slate-500 dark:text-slate-400 font-bold text-xs uppercase tracking-widest opacity-80">
                                        <span className="flex items-center gap-2"><Fingerprint size={14} className="text-[#6143f4]" /> ID: AR-992834</span>
                                        <span className="flex items-center gap-2"><Cake size={14} className="text-[#6143f4]" /> 12/05/1985 (38y)</span>
                                        <span className="flex items-center gap-2"><History size={14} className="text-[#6143f4]" /> LAST AUDIT: Oct 24, 2023</span>
                                    </div>
                                </div>
                            </div>
                            <div className="flex gap-4">
                                <button className="flex-1 sm:flex-none flex items-center justify-center gap-3 px-8 py-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-white/5 font-black text-[10px] uppercase tracking-[0.2em] text-[#13082a] dark:text-white hover:bg-slate-50 dark:hover:bg-slate-800 transition-all active:scale-95 shadow-xl shadow-slate-200/50 dark:shadow-none">
                                    <Share2 size={18} /> Share With MD
                                </button>
                                <button className="flex-1 sm:flex-none flex items-center justify-center gap-3 px-8 py-4 rounded-2xl bg-[#6143f4] text-white font-black text-[10px] uppercase tracking-[0.2em] hover:shadow-2xl hover:shadow-[#6143f4]/40 transition-all active:scale-95 leading-none">
                                    <FileDown size={18} /> Download PDF
                                </button>
                            </div>
                        </div>

                        {/* High-Level Assessment Cards Row */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
                            {[
                                { label: 'Overall Health Index', value: '82', sub: '/100', trend: '+5.2% Improvement', trendColor: 'text-green-600 bg-green-50 dark:bg-green-600/10', icon: TrendingUp },
                                { label: 'Active Pathologies', value: '2', sub: 'Detected', trend: 'Moderate Vigilance', trendColor: 'text-amber-600 bg-amber-50 dark:bg-amber-600/10', icon: AlertTriangle },
                                { label: 'AI Prediction Confidence', value: '98.4', sub: '%', trend: 'High Fidelity Analysis', trendColor: 'text-[#6143f4] bg-[#6143f4]/5 dark:bg-[#6143f4]/15', icon: Cpu },
                            ].map((stat, i) => (
                                <div key={i} className="p-8 rounded-[2.5rem] bg-white dark:bg-[#1a1433] border border-slate-100 dark:border-white/5 shadow-2xl shadow-slate-200/50 dark:shadow-none flex flex-col justify-between group hover:scale-[1.02] transition-all duration-500">
                                    <div>
                                        <p className="text-slate-400 font-black text-[10px] mb-3 uppercase tracking-[0.2em] opacity-80 leading-none">{stat.label}</p>
                                        <h3 className="text-5xl lg:text-6xl font-black text-[#13082a] dark:text-white tracking-tighter leading-none">
                                            {stat.value}<span className="text-xl text-slate-300 dark:text-slate-600 font-bold ml-1">{stat.sub}</span>
                                        </h3>
                                    </div>
                                    <div className={`mt-8 flex items-center gap-2 font-black text-[10px] uppercase tracking-widest ${stat.trendColor} px-4 py-2.5 rounded-xl w-fit shadow-sm`}>
                                        <stat.icon size={14} strokeWidth={2.5} /> {stat.trend}
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="grid grid-cols-12 gap-10">
                            {/* Detailed Risk Landscape Table Section */}
                            <div className="col-span-12 lg:col-span-8 space-y-10">
                                <section className="bg-white dark:bg-[#1a1433] rounded-[2.5rem] border border-slate-100 dark:border-white/5 shadow-2xl shadow-slate-200/50 dark:shadow-none overflow-hidden">
                                    <div className="px-10 py-8 border-b border-slate-50 dark:border-white/5 flex flex-col sm:flex-row justify-between items-center gap-4 bg-slate-50/30 dark:bg-white/2 overflow-hidden relative">
                                        <h2 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tight relative z-10">AI Disease Prediction Landscape</h2>
                                        <button className="text-[#6143f4] font-black text-[10px] uppercase tracking-[0.3em] hover:underline transition-all active:scale-95 py-2 px-6 bg-[#6143f4]/5 rounded-xl border border-[#6143f4]/10">Deep Model Metrics</button>
                                        <div className="absolute top-0 right-0 size-40 bg-[#6143f4] opacity-[0.03] blur-3xl -mr-20 -mt-20 rounded-full"></div>
                                    </div>
                                    <div className="overflow-x-auto">
                                        <table className="w-full text-left">
                                            <thead className="bg-slate-50/50 dark:bg-white/5 border-b border-slate-200 dark:border-slate-800">
                                                <tr>
                                                    <th className="px-10 py-6 text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Disease / Clinical State</th>
                                                    <th className="px-10 py-6 text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Risk Profile</th>
                                                    <th className="px-10 py-6 text-[10px] font-black text-slate-400 uppercase tracking-[0.3em]">Time Horizon</th>
                                                    <th className="px-10 py-6 text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] text-right">Probability</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                                {diseases.map((disease, i) => (
                                                    <tr key={i} className="hover:bg-slate-50/80 dark:hover:bg-white/5 transition-all group/row">
                                                        <td className="px-10 py-7">
                                                            <div className="font-black text-[#13082a] dark:text-white uppercase tracking-tight text-lg leading-none">{disease.name}</div>
                                                            <div className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-2 opacity-80 group-hover/row:text-[#6143f4] transition-colors leading-none flex items-center gap-1">
                                                                <span className="size-1 bg-[#6143f4] rounded-full"></span>
                                                                {disease.status}
                                                            </div>
                                                        </td>
                                                        <td className="px-10 py-7">
                                                            <span className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-[0.1em] shadow-sm border border-transparent ${disease.riskColor} flex items-center gap-2 w-fit`}>
                                                                {disease.risk === 'Critical High' && <AlertTriangle size={12} />}
                                                                {disease.risk}
                                                            </span>
                                                        </td>
                                                        <td className="px-10 py-7 text-slate-600 dark:text-slate-400 text-xs font-black uppercase tracking-[0.15em] leading-none">{disease.horizon}</td>
                                                        <td className="px-10 py-7 text-right font-black text-2xl text-[#13082a] dark:text-white tracking-tighter leading-none">{disease.probability}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </section>

                                {/* Deep Reasoning Narratives Section */}
                                <section className="bg-white dark:bg-[#1a1433] rounded-[2.5rem] border border-slate-100 dark:border-white/5 shadow-2xl shadow-slate-200/50 dark:shadow-none p-10 relative group overflow-hidden">
                                    <div className="absolute top-0 right-0 p-10 opacity-[0.02] group-hover:scale-125 transition-transform duration-1000">
                                        <Brain size={200} strokeWidth={1} />
                                    </div>
                                    <div className="flex items-center gap-4 mb-10 relative z-10">
                                        <div className="size-14 bg-[#009cde]/10 rounded-2xl flex items-center justify-center text-[#009cde] shadow-inner">
                                            <Brain size={28} strokeWidth={2.5} />
                                        </div>
                                        <h2 className="text-3xl font-black text-[#13082a] dark:text-white uppercase tracking-tight">AI Clinical Context Narratives</h2>
                                    </div>
                                    <div className="space-y-10 relative z-10">
                                        <p className="text-slate-600 dark:text-slate-300 leading-relaxed text-2xl font-medium tracking-tight">
                                            Our predictive engines have identified a <strong className="text-red-600 dark:text-red-500 font-black relative">
                                                Critical Volatility Signature
                                                <span className="absolute bottom-[-6px] left-0 w-full h-1.5 bg-red-100 dark:bg-red-900/40 -z-10 rounded-full"></span>
                                            </strong> for metabolic dysfunction. This determination is weighted by converging biometric and telemetry datasets.
                                        </p>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                            <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-white/5 border-l-8 border-[#6143f4] shadow-inner group/reason hover:bg-white dark:hover:bg-white/10 transition-colors duration-300">
                                                <h4 className="font-black text-[#13082a] dark:text-white text-xs uppercase tracking-widest mb-4 flex items-center gap-2">
                                                    <TrendingUp size={16} className="text-[#6143f4]" /> HbA1c Velocity Vector
                                                </h4>
                                                <p className="text-sm text-slate-500 dark:text-slate-400 font-bold italic leading-relaxed">Precision tracking shows an escalation from 5.4% to 5.8% (Pre-diabetic transition gate) over current trailing report cycles.</p>
                                            </div>
                                            <div className="p-8 rounded-[2.5rem] bg-slate-50 dark:bg-white/5 border-l-8 border-[#009cde] shadow-inner group/reason hover:bg-white dark:hover:bg-white/10 transition-colors duration-300">
                                                <h4 className="font-black text-[#13082a] dark:text-white text-xs uppercase tracking-widest mb-4 flex items-center gap-2">
                                                    <Activity size={16} className="text-[#009cde]" /> Cellular Resistance Decay
                                                </h4>
                                                <p className="text-sm text-slate-500 dark:text-slate-400 font-bold italic leading-relaxed">Telemetry data indicates post-prandial glucose peaks exceed physiological norms following metabolic glycemic loading events.</p>
                                            </div>
                                        </div>
                                        <div className="p-10 rounded-[3rem] bg-slate-900 dark:bg-black/40 text-white shadow-2xl relative overflow-hidden group/quote py-12">
                                            <div className="absolute top-0 right-0 p-8 opacity-10">
                                                <Quote size={80} strokeWidth={1} />
                                            </div>
                                            <p className="text-xl lg:text-2xl leading-relaxed italic font-medium opacity-90 relative z-10 max-w-2xl">
                                                "Trajectory analysis suggests a 74.2% semantic alignment with late-stage metabolic dysfunction signatures. Reversal requires calorie-restricted protocols and escalated Zone 2 cardiac output."
                                            </p>
                                            <div className="mt-8 flex items-center gap-3 relative z-10 opacity-70">
                                                <div className="h-px w-10 bg-white/30"></div>
                                                <span className="text-[10px] font-black uppercase tracking-[0.3em]">ArogyaAI Engine V4.2 Inference Unit</span>
                                            </div>
                                        </div>
                                    </div>
                                </section>
                            </div>

                            {/* Lifestyle Influence Sidebar Panel */}
                            <div className="col-span-12 lg:col-span-4 space-y-10">
                                <section className="bg-white dark:bg-[#1a1433] rounded-[2.5rem] border border-slate-100 dark:border-white/5 shadow-2xl shadow-slate-200/50 dark:shadow-none p-10 flex flex-col h-full overflow-hidden relative group">
                                    <div className="absolute top-0 right-0 size-40 bg-[#6143f4] opacity-[0.02] blur-3xl -mr-20 -mt-20 group-hover:opacity-[0.05] transition-opacity"></div>
                                    <h3 className="font-black text-[#13082a] dark:text-white mb-12 flex items-center gap-4 uppercase tracking-[0.2em] text-sm relative z-10 leading-none">
                                        <TrendingUp size={24} className="text-[#6143f4]" />
                                        Behavioral Impact Scores
                                    </h3>
                                    
                                    <div className="space-y-12 relative z-10">
                                        {[
                                            { icon: Moon, label: 'Sleep Efficiency', value: 45, status: 'DETRIMENTAL', color: 'bg-amber-400 shadow-amber-400/20', statusColor: 'text-amber-600 bg-amber-50 dark:bg-amber-600/10', note: 'Avg. 5.2h / night. Persistent cortisol spikes recorded in early REM.' },
                                            { icon: Dumbbell, label: 'Cardiac Output', value: 78, status: 'MITIGATING', color: 'bg-green-500 shadow-green-500/20', statusColor: 'text-green-600 bg-green-50 dark:bg-green-600/10', note: '180m/week Zone 2 consistency is buffering metabolic risk slope.' },
                                            { icon: Utensils, label: 'Glycemic Load Control', value: 32, status: 'CRITICAL RISK', color: 'bg-red-500 shadow-red-500/20', statusColor: 'text-red-600 bg-red-50 dark:bg-red-600/10', note: 'Persistent high-carb metabolic loading during post-audit cycles.' },
                                        ].map((metric, i) => (
                                            <div key={i} className="group/metric">
                                                <div className="flex justify-between items-end mb-4">
                                                    <div className="flex items-center gap-3">
                                                        <div className="size-8 rounded-lg bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400 group-hover/metric:text-[#6143f4] transition-colors shadow-inner">
                                                            <metric.icon size={16} />
                                                        </div>
                                                        <span className="font-black text-[10px] text-slate-500 dark:text-slate-400 uppercase tracking-widest opacity-80 leading-none">{metric.label}</span>
                                                    </div>
                                                    <span className={`${metric.statusColor} font-black text-[9px] px-3 py-1.5 rounded-full uppercase tracking-widest shadow-sm leading-none`}>{metric.status}</span>
                                                </div>
                                                <div className="h-3 w-full bg-slate-100 dark:bg-white/5 rounded-full overflow-hidden mb-4 shadow-inner border border-slate-50 dark:border-white/2">
                                                    <div className={`${metric.color} h-full rounded-full shadow-lg transition-all duration-1000 ease-out`} style={{ width: `${metric.value}%` }}></div>
                                                </div>
                                                <p className="text-[10px] text-slate-400 dark:text-slate-500 font-bold leading-relaxed italic opacity-80">{metric.note}</p>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="mt-auto pt-10 border-t border-slate-50 dark:border-white/5">
                                        <div className="p-8 rounded-[2.5rem] bg-[#6143f4]/5 dark:bg-[#6143f4]/15 flex items-start gap-5 border border-[#6143f4]/10 shadow-lg shadow-[#6143f4]/5 relative overflow-hidden group/tip">
                                            <Lightbulb size={24} className="text-[#6143f4] shrink-0 mt-1 animate-pulse" />
                                            <div className="relative z-10">
                                                <p className="text-[10px] font-black text-[#6143f4] mb-2 uppercase tracking-[0.2em] leading-none">CORE AI DIRECTIVE</p>
                                                <p className="text-xs leading-relaxed text-slate-600 dark:text-slate-300 font-bold italic">
                                                    "Stabilizing circadian alignment to 7.0h target will facilitate an immediate 12% reduction in basal metabolic volatility signatures."
                                                </p>
                                            </div>
                                            <div className="absolute top-0 right-0 size-20 bg-[#6143f4] opacity-[0.03] rounded-full blur-xl -mr-10 -mt-10 group-hover/tip:scale-150 transition-transform"></div>
                                        </div>
                                    </div>
                                </section>

                                {/* Compliance & Trust Footer Card */}
                                <div className="p-10 rounded-[2.5rem] bg-[#1a1433] dark:bg-black/50 text-white relative overflow-hidden group shadow-2xl border border-white/5">
                                    <div className="relative z-10">
                                        <div className="size-16 rounded-2xl bg-white/5 backdrop-blur-md flex items-center justify-center mb-8 border border-white/10 shadow-2xl group-hover:rotate-[360deg] transition-transform duration-1000 ease-in-out">
                                            <ShieldCheck size={32} className="text-white" strokeWidth={1.5} />
                                        </div>
                                        <h4 className="text-2xl font-black mb-4 tracking-tighter uppercase leading-none italic">Protocol Integrity</h4>
                                        <p className="text-sm text-slate-400 leading-relaxed font-bold opacity-80 mb-8 max-w-xs">
                                            This clinical report is encrypted via AES-256 GCM standards. 100% HIPAA and SOC2 compliant data transmission verified.
                                        </p>
                                        <button className="text-[10px] font-black text-[#6143f4] uppercase tracking-[0.3em] hover:text-white transition-all flex items-center gap-2 group-btn">
                                            Audit Security Certificate 
                                            <Share2 size={12} className="group-btn-hover:translate-x-1 transition-transform" />
                                        </button>
                                    </div>
                                    <div className="absolute -bottom-20 -right-20 size-60 bg-[#6143f4] opacity-10 rounded-full blur-[80px] group-hover:scale-150 transition-transform duration-1000"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>

            {/* Mobile Actions Overlay - Matched Stitch */}
            <div className="lg:hidden sticky bottom-0 left-0 right-0 bg-white dark:bg-[#131022] border-t border-slate-100 dark:border-slate-800 p-6 grid grid-cols-2 gap-4 z-50 shadow-[0_-15px_40px_rgba(0,0,0,0.1)]">
                <button className="flex items-center justify-center gap-3 py-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-white/5 font-black text-[11px] uppercase tracking-[0.2em] text-[#13082a] dark:text-white active:scale-95 transition-all shadow-sm">
                    <Share2 size={18} /> share report
                </button>
                <button className="flex items-center justify-center gap-3 py-4 rounded-2xl bg-[#6143f4] text-white font-black text-[11px] uppercase tracking-[0.2em] active:scale-95 transition-all shadow-xl shadow-[#6143f4]/30">
                    <FileDown size={18} /> pdf summary
                </button>
            </div>

            <style dangerouslySetInnerHTML={{ __html: `
                .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .leading-none { line-height: 1 !important; }
            `}} />
        </div>
    );
};

export default AIRiskReport;

