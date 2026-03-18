import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Brain, 
  Activity, 
  History, 
  FlaskConical, 
  FileText, 
  Settings, 
  Search, 
  Bell, 
  Upload, 
  ChevronRight, 
  Sparkles, 
  ExternalLink,
  HeartPulse,
  TrendingUp,
  AlertTriangle,
  Beaker
} from 'lucide-react';
import { ROUTES } from '../router/routes';

const LabResults = () => {
    const navigate = useNavigate();
    const [activeFilter, setActiveFilter] = useState('All Tests');

    const filters = ['All Tests', 'Hematology', 'Biochemistry', 'Metabolic', 'Lipid Profile', 'Thyroid'];

    const labData = [
        {
            parameter: 'Hemoglobin (Hb)',
            category: 'HEMATOLOGY',
            value: '14.2',
            unit: 'g/dL',
            range: '13.5 - 17.5',
            status: 'Normal',
            statusColor: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200/50',
            statusBg: 'bg-emerald-500',
            trend: [60, 65, 72, 68, 75, 70]
        },
        {
            parameter: 'Glucose (Fasting)',
            category: 'METABOLIC',
            value: '110',
            unit: 'mg/dL',
            range: '70 - 99',
            status: 'Borderline',
            statusColor: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border-amber-200/50',
            statusBg: 'bg-amber-500',
            trend: [40, 45, 55, 65, 75, 85]
        },
        {
            parameter: 'LDL Cholesterol',
            category: 'LIPID PROFILE',
            value: '165',
            unit: 'mg/dL',
            range: '< 100',
            status: 'High',
            statusColor: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border-red-200/50',
            statusBg: 'bg-red-500',
            trend: [60, 62, 68, 75, 88, 95]
        },
        {
            parameter: 'TSH',
            category: 'THYROID',
            value: '2.5',
            unit: 'uIU/mL',
            range: '0.4 - 4.0',
            status: 'Normal',
            statusColor: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-200/50',
            statusBg: 'bg-emerald-500',
            trend: [50, 48, 52, 50, 55, 53]
        }
    ];

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS },
        { icon: FlaskConical, label: 'Simulator', path: ROUTES.SIMULATOR },
        { icon: History, label: 'Timeline', path: ROUTES.TIMELINE },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, active: true },
        { icon: FileText, label: 'Reports', path: ROUTES.MEDICAL_REPORTS },
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}
                <aside className="w-72 bg-white dark:bg-[#131022] border-r border-[#6143f4]/5 dark:border-slate-800 flex flex-col shrink-0 hidden lg:flex">
                    <div className="p-8 flex items-center gap-4 cursor-pointer group" onClick={() => navigate(ROUTES.DASHBOARD)}>
                        <div className="size-11 bg-[#6143f4] rounded-xl flex items-center justify-center text-white shadow-lg shadow-[#6143f4]/20 transition-transform group-hover:scale-110">
                            <HeartPulse size={24} strokeWidth={2.5} />
                        </div>
                        <div>
                            <h1 className="text-xl font-black tracking-tight leading-none uppercase">ArogyaAI</h1>
                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-[0.2em] mt-1">Health Intelligence</p>
                        </div>
                    </div>
                    <nav className="flex-1 px-5 py-4 space-y-1.5 overflow-y-auto custom-scrollbar">
                        {sidebarLinks.map((link) => (
                            <button
                                key={link.label}
                                onClick={() => navigate(link.path)}
                                className={`w-full flex items-center gap-3.5 px-4 py-3.5 rounded-xl transition-all group ${
                                    link.active 
                                    ? 'bg-[#6143f4] text-white shadow-xl shadow-[#6143f4]/20 font-black' 
                                    : 'text-slate-500 dark:text-slate-400 hover:bg-[#6143f4]/5 hover:text-[#6143f4] font-bold'
                                }`}
                            >
                                <link.icon size={18} className={link.active ? 'text-white' : 'text-slate-400 group-hover:text-[#6143f4]'} />
                                <span className="text-[11px] uppercase tracking-widest leading-none">{link.label}</span>
                            </button>
                        ))}
                    </nav>
                    <div className="p-6 border-t border-slate-100 dark:border-slate-800">
                        <button className="w-full flex items-center gap-3.5 px-4 py-3.5 text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5 rounded-xl transition-all font-bold group">
                            <Settings size={18} className="text-slate-400 group-hover:text-primary" />
                            <span className="text-[11px] uppercase tracking-widest leading-none">Settings Hub</span>
                        </button>
                    </div>
                </aside>

                {/* Main Content Area */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* Top Navbar - Standardized */}
                    <header className="h-20 bg-white/80 dark:bg-[#131022]/80 backdrop-blur-md border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 z-10">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group">
                                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-12 pr-6 py-3 bg-slate-100 dark:bg-white/5 border-none rounded-2xl text-sm font-medium focus:ring-2 focus:ring-[#6143f4]/20 transition-all placeholder:text-slate-400 outline-none" placeholder="Search lab parameters, dates or providers..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-8">
                            <button className="size-11 flex items-center justify-center rounded-2xl bg-slate-100 dark:bg-white/5 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-90 group">
                                <Bell size={20} />
                                <span className="absolute top-3 right-3 size-2.5 bg-red-500 rounded-full border-2 border-white dark:border-[#131022] group-hover:scale-110 transition-transform"></span>
                            </button>
                            <div className="h-8 w-px bg-slate-200 dark:bg-slate-800 hidden md:block"></div>
                            <div className="flex items-center gap-4 cursor-pointer group" onClick={() => navigate(ROUTES.SETTINGS)}>
                                <div className="text-right hidden sm:block">
                                    <p className="text-sm font-black text-[#13082a] dark:text-white leading-none uppercase group-hover:text-[#6143f4] transition-colors">Alex Johnson</p>
                                    <p className="text-[9px] text-slate-500 mt-1.5 uppercase tracking-[0.2em] font-black opacity-70">Patient ID: AR-992834</p>
                                </div>
                                <div className="size-11 rounded-2xl bg-[#6143f4]/10 border-2 border-transparent group-hover:border-[#6143f4] overflow-hidden transition-all shadow-md group-hover:scale-110">
                                    <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBSNEjoorIjStYduz4toUoH9taRezR9gUmeBlfZqgLvFpq-7Dpa-im_yfn3lhwmaedZOiCg-PEuJeDdpULcssnht9u6CnykpHhZffrOhUXsuZ9iTanq55ms_jcerh6Lq3TN4Or7exJuJ0BaCCElRYRK3NBThOT8RXKoJqVsW5ZC_1R8GCbXb1IaZTElgrP9NB2hNpAClQTc6gsxVwCZJx56bTPuLyvxxphaTbQKe2pAiZg6dxh0LvCzzUm-NNDqI7e0fgO5Z4StDAON" alt="User Profile" />
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Scrollable Content */}
                    <div className="flex-1 overflow-y-auto p-10 custom-scrollbar bg-[#f6f5f8] dark:bg-[#131022]">
                        <div className="max-w-7xl mx-auto space-y-12 pb-12">
                            {/* Title and Actions */}
                            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8">
                                <div>
                                    <div className="flex items-center gap-3 mb-2">
                                        <Beaker size={16} className="text-[#6143f4]" />
                                        <p className="text-[10px] text-slate-500 font-black uppercase tracking-[0.3em]">Diagnostic Insights</p>
                                    </div>
                                    <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase leading-none">Lab Test Results</h2>
                                    <p className="text-slate-400 mt-4 font-bold uppercase tracking-widest text-[11px] opacity-80">View and analyze your latest clinical diagnostic data landscape</p>
                                </div>
                                <button 
                                    onClick={() => navigate(ROUTES.UPLOAD)}
                                    className="bg-[#6143f4] hover:bg-[#4a34c1] text-white px-10 py-5 rounded-[1.25rem] font-black text-[11px] uppercase tracking-[0.25em] flex items-center gap-4 shadow-2xl shadow-[#6143f4]/30 transition-all active:scale-95 whitespace-nowrap leading-none"
                                >
                                    <Upload size={18} strokeWidth={3} />
                                    Upload New Report
                                </button>
                            </div>

                            {/* Filters - Matched Stitch Pill Style */}
                            <div className="flex flex-wrap items-center gap-2.5 p-2 bg-white dark:bg-white/5 rounded-[1.5rem] w-fit border border-slate-100 dark:border-white/5 shadow-xl shadow-slate-200/40 dark:shadow-none">
                                {filters.map((filter) => (
                                    <button
                                        key={filter}
                                        onClick={() => setActiveFilter(filter)}
                                        className={`px-7 py-3 rounded-[1rem] text-[10px] font-black uppercase tracking-widest transition-all ${
                                            activeFilter === filter 
                                            ? 'bg-[#6143f4] text-white shadow-xl shadow-[#6143f4]/20 scale-105' 
                                            : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-white/5'
                                        }`}
                                    >
                                        {filter}
                                    </button>
                                ))}
                            </div>

                            {/* Results Table Container */}
                            <section className="bg-white dark:bg-[#1a1433] rounded-[3rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-2xl shadow-slate-200/50 dark:shadow-none">
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left border-collapse">
                                        <thead>
                                            <tr className="bg-slate-50/50 dark:bg-white/5 border-b border-slate-200 dark:border-slate-800">
                                                <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Parameter / Category</th>
                                                <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Last Result</th>
                                                <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 text-center">Referential Range</th>
                                                <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Status State</th>
                                                <th className="px-10 py-7 text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Trend (6 Month)</th>
                                                <th className="px-10 py-7 w-20"></th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                            {labData.map((item, index) => (
                                                <tr key={index} className="hover:bg-slate-50/70 dark:hover:bg-white/5 transition-all group/row cursor-pointer relative">
                                                    <td className="px-10 py-7">
                                                        <div className="flex flex-col">
                                                            <span className="font-black text-[#13082a] dark:text-white uppercase tracking-tight text-lg leading-none">{item.parameter}</span>
                                                            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-2 flex items-center gap-1 opacity-70 group-hover/row:text-[#6143f4] transition-colors leading-none">
                                                                <span className="size-1 bg-[#6143f4] rounded-full mr-1"></span>
                                                                {item.category}
                                                            </span>
                                                        </div>
                                                    </td>
                                                    <td className="px-10 py-7">
                                                        <span className="text-2xl font-black tracking-tighter text-[#13082a] dark:text-white leading-none">
                                                            {item.value} <span className="text-[11px] font-bold text-slate-400 uppercase tracking-widest ml-1">{item.unit}</span>
                                                        </span>
                                                    </td>
                                                    <td className="px-10 py-7 text-center">
                                                        <span className="text-[10px] font-black text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-white/5 px-5 py-2 rounded-full uppercase tracking-widest border border-slate-200 dark:border-slate-800 leading-none">
                                                            {item.range}
                                                        </span>
                                                    </td>
                                                    <td className="px-10 py-7">
                                                        <span className={`inline-flex items-center gap-2.5 px-5 py-2 rounded-full text-[10px] font-black uppercase tracking-[0.1em] shadow-sm border border-transparent ${item.statusColor} leading-none`}>
                                                            <span className={`size-2 rounded-full ${item.statusBg} animate-pulse`}></span>
                                                            {item.status}
                                                        </span>
                                                    </td>
                                                    <td className="px-10 py-7">
                                                        <div className="flex items-end gap-1.5 h-10 w-32">
                                                            {item.trend.map((val, i) => (
                                                                <div 
                                                                    key={i} 
                                                                    className={`w-1.5 rounded-full transition-all duration-700 ease-out group-hover/row:scale-y-125 ${
                                                                        item.status === 'Normal' ? 'bg-[#6143f4]' : 
                                                                        item.status === 'Borderline' ? 'bg-amber-500' : 'bg-red-500'
                                                                    }`}
                                                                    style={{ 
                                                                        height: `${val}%`, 
                                                                        opacity: (i + 1) * 0.15 + 0.1,
                                                                        transitionDelay: `${i * 50}ms`
                                                                    }}
                                                                ></div>
                                                            ))}
                                                        </div>
                                                    </td>
                                                    <td className="px-10 py-7 text-right">
                                                        <div className="size-10 rounded-xl bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-300 dark:text-slate-600 group-hover/row:bg-[#6143f4]/10 group-hover/row:text-[#6143f4] group-hover/row:scale-110 transition-all opacity-0 md:opacity-100 transform translate-x-4 group-hover/row:translate-x-0">
                                                            <ChevronRight size={20} strokeWidth={3} />
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </section>

                            {/* Deep Insights and Trajectory Area */}
                            <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
                                {/* AI Health Summary Section */}
                                <div className="lg:col-span-8 bg-gradient-to-br from-[#6143f4] to-[#4a34c1] rounded-[3rem] p-12 text-white shadow-2xl shadow-[#6143f4]/30 relative overflow-hidden group">
                                    <div className="relative z-10 h-full flex flex-col justify-between">
                                        <div>
                                            <div className="flex items-center gap-4 mb-8">
                                                <div className="size-14 bg-white/15 backdrop-blur-xl rounded-2xl flex items-center justify-center shadow-inner border border-white/10">
                                                    <Sparkles size={28} className="text-white" strokeWidth={2.5} />
                                                </div>
                                                <h3 className="text-3xl font-black uppercase tracking-tight leading-none">AI Health Summary</h3>
                                            </div>
                                            <p className="text-white/90 leading-relaxed text-2xl font-medium mb-12 max-w-2xl tracking-tight">
                                                Your <strong className="font-black text-white relative">
                                                    LDL Cholesterol
                                                    <span className="absolute bottom-[-4px] left-0 w-full h-1 bg-white/30 rounded-full"></span>
                                                </strong> has increased by 15% over the last 3 months. While metabolic markers remain within borderline ranges, we recommend immediate focus on heart-healthy fats and escalated cardiovascular output.
                                            </p>
                                        </div>
                                        <div className="flex flex-wrap gap-8">
                                            <div className="bg-white/10 backdrop-blur-2xl rounded-[2rem] px-10 py-6 border border-white/20 shadow-xl transition-transform hover:scale-105">
                                                <div className="flex items-center gap-2 mb-3">
                                                    <TrendingUp size={14} className="text-white/60" />
                                                    <p className="text-[10px] text-white/60 uppercase font-black tracking-[0.2em] leading-none">Next Checkup Target</p>
                                                </div>
                                                <p className="text-2xl font-black tracking-tight leading-none">April 12, 2024</p>
                                            </div>
                                            <div className="bg-white/10 backdrop-blur-2xl rounded-[2rem] px-10 py-6 border border-white/20 shadow-xl transition-transform hover:scale-105">
                                                <div className="flex items-center gap-2 mb-3">
                                                    <Activity size={14} className="text-white/60" />
                                                    <p className="text-[10px] text-white/60 uppercase font-black tracking-[0.2em] leading-none">Priority Priority</p>
                                                </div>
                                                <p className="text-2xl font-black tracking-tight uppercase leading-none">Lipid Profile</p>
                                            </div>
                                        </div>
                                    </div>
                                    {/* Abstract Visuals */}
                                    <div className="absolute top-0 right-0 size-96 bg-white/10 rounded-full -mr-32 -mt-32 blur-[100px] group-hover:scale-110 transition-transform duration-1000"></div>
                                    <div className="absolute bottom-0 left-0 size-64 bg-black/20 rounded-full -ml-20 -mb-20 blur-[80px]"></div>
                                </div>

                                {/* Historical View Sidebar Item */}
                                <div className="lg:col-span-4 bg-white dark:bg-[#1a1433] border border-slate-100 dark:border-white/5 rounded-[3rem] p-10 shadow-2xl shadow-slate-200/50 dark:shadow-none relative group overflow-hidden flex flex-col justify-between">
                                    <div className="relative z-10">
                                        <div className="flex items-center justify-between mb-10">
                                            <h3 className="font-black text-[#13082a] dark:text-white uppercase tracking-widest text-xs leading-none">Historical Trajectory</h3>
                                            <button className="text-[#6143f4] text-[10px] font-black uppercase tracking-widest flex items-center gap-2 hover:underline transition-all group/btn">
                                                Full Analytics
                                                <ExternalLink size={12} className="group-btn-hover:translate-x-0.5 transition-transform" />
                                            </button>
                                        </div>
                                        
                                        <div className="space-y-10">
                                            <div>
                                                <div className="flex justify-between items-center mb-6">
                                                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest leading-none">Selected Parameter</span>
                                                    <span className="text-[10px] font-black bg-[#6143f4]/10 text-[#6143f4] px-4 py-2 rounded-full uppercase tracking-widest border border-[#6143f4]/10 leading-none">LDL Cholesterol</span>
                                                </div>
                                                <div className="h-44 w-full bg-slate-50 dark:bg-black/20 rounded-[2rem] flex items-end justify-between px-8 pb-6 border border-slate-100 dark:border-white/5 shadow-inner group/chart overflow-hidden">
                                                    {[50, 62, 68, 82, 88, 100].map((h, i) => (
                                                        <div 
                                                            key={i}
                                                            className={`w-2.5 rounded-t-full transition-all duration-1000 ${
                                                                i === 5 ? 'bg-[#6143f4] shadow-xl shadow-[#6143f4]/30' : 'bg-[#6143f4]/20 group-hover/chart:bg-[#6143f4]/40'
                                                            }`}
                                                            style={{ 
                                                                height: `${h}%`, 
                                                                transitionDelay: `${i * 75}ms` 
                                                            }}
                                                        ></div>
                                                    ))}
                                                </div>
                                                <div className="flex justify-between mt-5 px-3 text-[10px] text-slate-400 font-black uppercase tracking-[0.25em] opacity-80 leading-none">
                                                    <span>Oct</span>
                                                    <span>Dec</span>
                                                    <span>Feb</span>
                                                    <span className="text-[#6143f4]">Mar</span>
                                                </div>
                                            </div>
                                            <div className="pt-8 border-t border-slate-100 dark:border-white/5">
                                                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed italic font-bold opacity-80 max-w-[240px]">
                                                    "Your LDL show a persistent escalation vector. Inference recommends immediate dietary calibration."
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="absolute top-0 right-0 size-40 bg-[#6143f4] opacity-[0.03] blur-3xl -mr-20 -mt-20 group-hover:opacity-[0.06] transition-opacity"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
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

export default LabResults;
