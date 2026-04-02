import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Brain, 
  FlaskConical, 
  History, 
  Activity, 
  FileText, 
  Settings, 
  Search, 
  Bell, 
  Plus, 
  FileCheck, 
  Eye, 
  ZoomIn, 
  Download, 
  Image as LucideImage, 
  FileMinus,
  ArrowRight,
  Verified,
  Sparkles,
  Lock,
  QrCode,
  Moon,
  ChevronRight,
  ClipboardList
} from 'lucide-react';
import { ROUTES } from '../router/routes';

const Reports = () => {
    const navigate = useNavigate();
    const [selectedReport, setSelectedReport] = useState('Hematology_Panel_Q1.pdf');

    const reports = [
        { id: 'Hematology_Panel_Q1.pdf', type: 'pdf', date: 'Jan 12, 2024', size: '2.4 MB', status: 'OCR PROCESSED', statusColor: 'bg-emerald-100 text-emerald-700 border-emerald-200/50', active: true },
        { id: 'Chest_XRay_Scan.jpg', type: 'image', date: 'Jan 10, 2024', size: '5.1 MB', status: 'SCANNING...', statusColor: 'bg-amber-100 text-amber-700 border-amber-200/50' },
        { id: 'Annual_Checkup_Full.pdf', type: 'pdf', date: 'Dec 28, 2023', size: '12.0 MB', status: 'ARCHIVED', statusColor: 'bg-slate-200 text-slate-600 border-slate-300/50', archived: true },
        { id: 'Cardiology_Echo_02.pdf', type: 'pdf', date: 'Dec 15, 2023', size: '3.8 MB', status: 'OCR PROCESSED', statusColor: 'bg-emerald-100 text-emerald-700 border-emerald-200/50' },
        { id: 'Skin_Dermatology_Report.png', type: 'image', date: 'Nov 30, 2023', size: '1.1 MB', status: 'PROCESSED', statusColor: 'bg-emerald-100 text-emerald-700 border-emerald-200/50' },
    ];

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, active: true },
        { icon: Moon, label: 'Sleep Analysis', path: ROUTES.SLEEP },
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <div className="flex-1 flex flex-col min-w-0">
                    {/* Top Navbar */}
                    <header className="h-24 bg-white/40 dark:bg-[#131022]/40 backdrop-blur-2xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 z-10">
                        <div className="flex items-center gap-6 flex-1 max-w-2xl">
                            <div className="relative w-full group">
                                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={20} />
                                <input className="w-full pl-14 pr-7 py-4 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[1.75rem] focus:ring-4 focus:ring-[#6143f4]/10 outline-none transition-all shadow-xl shadow-slate-200/30 dark:shadow-none placeholder:text-slate-400 font-medium" placeholder="Search reports, clinics, or diagnosis..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-8">
                            <button className="relative size-12 flex items-center justify-center text-slate-500 dark:text-slate-400 hover:bg-white dark:hover:bg-white/5 rounded-2xl transition-all shadow-xl shadow-slate-200/30 dark:shadow-none active:scale-95 group">
                                <Bell size={22} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-red-500 rounded-full border-2 border-white dark:border-[#131022] animate-pulse"></span>
                            </button>
                            <div className="h-10 w-px bg-slate-200 dark:bg-white/5 hidden sm:block"></div>
                            <div className="flex items-center gap-4 group cursor-pointer" onClick={() => navigate(ROUTES.SETTINGS)}>
                                <div className="text-right hidden sm:block">
                                    <p className="text-sm font-black text-[#13082a] dark:text-white leading-none uppercase group-hover:text-[#6143f4] transition-colors tracking-tight italic">Dr. Sarah Chen</p>
                                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-1.5 opacity-80 leading-none">Head of Cardiology</p>
                                </div>
                                <div className="size-12 rounded-[1.25rem] bg-[#6143f4]/10 overflow-hidden border-2 border-transparent group-hover:border-[#6143f4] shadow-2xl transition-all group-hover:scale-110 group-active:scale-95 group-hover:rotate-3">
                                    <img className="w-full h-full object-cover" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAq6-7j0ca9q9TIm8c_65_71OK_end-RsZzJ-J-ZRyUq8frKpBG3_cusF7FwKlQ1TXdIhnz04w6gN1FZNDlCFYxWXZswJcAwEZcfgM_AGNKGehADmBKbzDD357dAd17Obt03b0MXiw68tGcZ0Vr95mLzjQ_61NVq62x7xGp6SbdhqF3kScuEbRTtIm_zn_fzPBtzZ54LFxJBRpDVGG5-oyVNWpuyiCL1yJTmyzb6zKkAhu-0xlWykdN1GZpk4kw2VtwNugx6IiI5Zj8" alt="Dr. Sarah Chen" />
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Content Section */}
                    <div className="flex-1 overflow-hidden flex flex-col">
                        <div className="flex flex-col md:flex-row md:items-center justify-between px-10 py-10 shrink-0 gap-6">
                            <div>
                                <h2 className="text-4xl lg:text-5xl font-black tracking-tighter uppercase text-[#13082a] dark:text-white leading-none italic">Medical Reports Hub</h2>
                                <p className="text-slate-400 font-bold uppercase tracking-[0.25em] text-[11px] mt-4 opacity-80 leading-none">Manage and analyze clinical diagnostics via AI Extraction engines</p>
                            </div>
                            <button 
                                onClick={() => navigate(ROUTES.UPLOAD)}
                                className="bg-[#6143f4] hover:bg-[#4a34c1] text-white px-9 py-5 rounded-[1.5rem] font-black text-[11px] uppercase tracking-[0.25em] flex items-center gap-4 transition-all shadow-2xl shadow-[#6143f4]/40 active:scale-95 group leading-none"
                            >
                                <Plus size={18} strokeWidth={3} className="group-hover:rotate-90 transition-transform" />
                                Upload New Report
                            </button>
                        </div>

                        <div className="flex flex-1 gap-10 px-10 pb-10 overflow-hidden">
                            {/* Report Sidebar List - 35% Width */}
                            <div className="w-[35%] flex flex-col gap-4 overflow-y-auto pr-4 custom-scrollbar">
                                {reports.map((report) => (
                                    <div 
                                        key={report.id}
                                        onClick={() => setSelectedReport(report.id)}
                                        className={`p-6 rounded-[2.25rem] border transition-all cursor-pointer flex items-center gap-5 group shadow-xl ${
                                            selectedReport === report.id 
                                            ? 'bg-white dark:bg-white/10 border-[#6143f4] shadow-[#6143f4]/15' 
                                            : 'bg-white/60 dark:bg-white/5 border-transparent hover:border-slate-200 dark:hover:border-white/10 shadow-slate-200/30 dark:shadow-none'
                                        }`}
                                    >
                                        <div className={`size-14 rounded-[1.25rem] flex items-center justify-center shadow-inner transition-transform group-hover:scale-110 ${
                                            report.type === 'pdf' ? 'bg-red-50 text-red-500' : 'bg-[#009cde]/10 text-[#009cde]'
                                        }`}>
                                            {report.type === 'pdf' ? <FileText size={24} strokeWidth={2.5} /> : <LucideImage size={24} strokeWidth={2.5} />}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <h4 className="font-black text-[#13082a] dark:text-white text-[15px] tracking-tight truncate leading-none mb-2">{report.id}</h4>
                                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest leading-none">{report.date} • {report.size}</p>
                                        </div>
                                        <div>
                                            <span className={`px-4 py-2 rounded-full text-[9px] font-black uppercase tracking-widest shadow-sm border ${report.statusColor} leading-none`}>
                                                {report.status}
                                            </span>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Center Preview and Right Data Panels */}
                            <div className="flex-1 flex gap-10 overflow-hidden">
                                {/* Preview Container */}
                                <div className="flex-1 bg-white/40 dark:bg-white/5 backdrop-blur-2xl rounded-[3rem] overflow-hidden flex flex-col shadow-2xl border border-white/40 dark:border-white/10 relative group">
                                    <div className="p-7 bg-white/40 dark:bg-white/5 border-b border-white/20 dark:border-white/10 flex items-center justify-between relative z-10">
                                        <div className="flex items-center gap-4">
                                            <div className="size-8 bg-[#6143f4]/10 rounded-lg flex items-center justify-center text-[#6143f4]">
                                                <Eye size={18} />
                                            </div>
                                            <span className="text-[10px] font-black uppercase tracking-[0.25em] text-slate-500 dark:text-slate-400 leading-none">
                                                Previewing: <span className="text-[#13082a] dark:text-white opacity-100">{selectedReport}</span>
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <button className="p-2.5 hover:bg-white dark:hover:bg-white/10 rounded-xl text-slate-500 dark:text-slate-400 transition-all active:scale-90 border border-transparent hover:border-slate-100">
                                                <ZoomIn size={18} />
                                            </button>
                                            <button className="p-2.5 hover:bg-white dark:hover:bg-white/10 rounded-xl text-slate-500 dark:text-slate-400 transition-all active:scale-90 border border-transparent hover:border-slate-100">
                                                <Download size={18} />
                                            </button>
                                        </div>
                                    </div>
                                    <div className="flex-1 overflow-hidden p-10 flex items-center justify-center bg-slate-100/40 dark:bg-black/20">
                                        <div className="w-full h-full bg-white dark:bg-[#1a1433] rounded-[2.5rem] shadow-2xl relative overflow-hidden flex flex-col border border-slate-200 dark:border-white/5 p-12 transition-transform group-hover:scale-[0.99] duration-700">
                                            <div className="w-32 h-6 bg-slate-200 dark:bg-slate-800 rounded-lg mb-10 opacity-30 animate-pulse"></div>
                                            <div className="flex justify-between mb-16">
                                                <div className="space-y-4">
                                                    <div className="w-56 h-4 bg-slate-100 dark:bg-slate-800 rounded-lg opacity-50"></div>
                                                    <div className="w-40 h-4 bg-slate-100 dark:bg-slate-800 rounded-lg opacity-50"></div>
                                                </div>
                                                <div className="size-24 border-4 border-slate-50 dark:border-slate-800 rounded-[2rem] opacity-20 flex items-center justify-center">
                                                    <QrCode size={40} />
                                                </div>
                                            </div>
                                            <div className="space-y-7 flex-1">
                                                <div className="flex items-center gap-8">
                                                    <div className="w-1/4 h-5 bg-slate-200/50 dark:bg-slate-800/50 rounded-lg"></div>
                                                    <div className="flex-1 h-5 bg-[#6143f4]/10 rounded-full"></div>
                                                </div>
                                                <div className="flex items-center gap-8">
                                                    <div className="w-1/4 h-5 bg-slate-200/50 dark:bg-slate-800/50 rounded-lg"></div>
                                                    <div className="flex-1 h-5 bg-[#6143f4]/10 rounded-full"></div>
                                                </div>
                                                <div className="h-px bg-slate-200 dark:bg-slate-800 my-10"></div>
                                                <div className="w-full flex-1 bg-slate-50/50 dark:bg-black/20 rounded-[2.5rem] border-2 border-dashed border-slate-200 dark:border-slate-800 flex flex-col items-center justify-center gap-5">
                                                    <Lock size={48} className="text-slate-300 dark:text-slate-700" strokeWidth={1.5} />
                                                    <p className="text-[11px] text-slate-400 dark:text-slate-600 uppercase tracking-[0.4em] font-black">Encrypted Clinical Payload</p>
                                                </div>
                                            </div>
                                            {/* Preview Overlay Polish */}
                                            <div className="absolute inset-0 bg-white/5 dark:bg-black/5 backdrop-blur-[2px] pointer-events-none"></div>
                                        </div>
                                    </div>
                                </div>

                                {/* AI OCR EXTRACTED Panel - Right 320px */}
                                <div className="w-80 bg-white/40 dark:bg-white/5 backdrop-blur-2xl rounded-[3rem] p-9 shadow-2xl flex flex-col border border-white/40 dark:border-white/10 relative group">
                                    <div className="flex items-center gap-4 mb-10 relative z-10">
                                        <div className="size-11 bg-[#6143f4]/10 rounded-xl flex items-center justify-center text-[#6143f4] shadow-inner">
                                            <Sparkles size={20} className="animate-pulse" />
                                        </div>
                                        <h3 className="text-xs font-black uppercase tracking-[0.25em] text-[#13082a] dark:text-white leading-none">AI OCR EXTRACTED</h3>
                                    </div>
                                    <div className="space-y-9 flex-1 overflow-y-auto pr-2 custom-scrollbar relative z-10">
                                        <div>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 opacity-80 leading-none">Identified Patient</p>
                                            <p className="text-xl font-black text-[#13082a] dark:text-white tracking-tight leading-none italic underline decoration-[#6143f4]/30 decoration-4 underline-offset-4">Alexander Thorne</p>
                                        </div>
                                        <div>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 opacity-80 leading-none">Extraction Timestamp</p>
                                            <p className="text-xl font-black text-[#13082a] dark:text-white tracking-tight leading-none italic">Jan 11, 2024</p>
                                        </div>
                                        <div className="p-7 bg-[#009cde]/5 dark:bg-[#009cde]/10 rounded-[2.25rem] border border-[#009cde]/15 shadow-xl shadow-[#009cde]/5 relative overflow-hidden group/findings">
                                            <div className="absolute top-0 right-0 size-20 bg-[#009cde] opacity-[0.03] blur-2xl -mr-10 -mt-10 group-hover/findings:opacity-[0.1] transition-opacity"></div>
                                            <p className="text-[10px] font-black text-[#009cde] uppercase tracking-[0.25em] mb-5 leading-none flex items-center gap-2">
                                                <ClipboardList size={14} /> Forensic Findings
                                            </p>
                                            <ul className="text-[11px] space-y-4 text-slate-600 dark:text-slate-300 font-bold leading-relaxed">
                                                <li className="flex gap-3">
                                                    <span className="text-[#009cde] font-black">•</span>
                                                    <span>Elevated hemoglobin levels detected (17.5 g/dL).</span>
                                                </li>
                                                <li className="flex gap-3">
                                                    <span className="text-[#009cde] font-black">•</span>
                                                    <span>WBC count within safety bounds.</span>
                                                </li>
                                                <li className="flex gap-3">
                                                    <span className="text-[#009cde] font-black">•</span>
                                                    <span className="text-red-500 underline decoration-red-200 dark:decoration-red-900 leading-tight">Vitamin D deficiency noted; supplement recommended.</span>
                                                </li>
                                            </ul>
                                        </div>
                                        <div>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-5 opacity-80 leading-none">Biometric Delta Map</p>
                                            <div className="space-y-4">
                                                {[
                                                    { label: 'Glucose (F)', val: '92 mg/dL', color: 'text-emerald-500' },
                                                    { label: 'Creatinine', val: '0.9 mg/dL', color: 'text-slate-500 dark:text-slate-400' },
                                                    { label: 'Hemoglobin', val: '17.5 g/dL ↑', color: 'text-red-500 font-black' },
                                                ].map((m, i) => (
                                                    <div key={i} className="flex items-center justify-between text-xs py-1 border-b border-slate-100 dark:border-white/5 last:border-0 group/biometric">
                                                        <span className="font-bold text-slate-400 uppercase tracking-widest text-[10px] group-hover/biometric:text-[#6143f4] transition-colors">{m.label}</span>
                                                        <span className={`${m.color} font-black tracking-tight`}>{m.val}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="pt-8 border-t border-slate-100 dark:border-white/10 mt-8 relative z-10">
                                        <button className="w-full py-5 bg-[#13082a] dark:bg-[#6143f4] text-white rounded-[1.25rem] text-[10px] font-black uppercase tracking-[0.3em] hover:shadow-2xl hover:shadow-[#6143f4]/40 transition-all active:scale-95 flex items-center justify-center gap-3 group/btn">
                                            <Verified size={18} strokeWidth={2.5} className="group-hover/btn:scale-110 transition-transform" />
                                            Validate Data
                                            <ArrowRight size={14} className="group-hover/btn:translate-x-1 transition-transform" />
                                        </button>
                                    </div>
                                    <div className="absolute bottom-0 right-0 size-40 bg-[#6143f4] opacity-[0.02] blur-3xl -mr-20 -mb-20"></div>
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

export default Reports;
