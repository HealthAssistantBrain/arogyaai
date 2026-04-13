import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Activity, 
  LayoutDashboard, 
  BarChart2, 
  FlaskConical, 
  FolderOpen, 
  Settings, 
  Search, 
  Bell, 
  Plus, 
  ChevronRight, 
  ChevronsUpDown, 
  FileText, 
  Cpu, 
  Stethoscope, 
  BadgeCheck, 
  MessageSquare, 
  BarChart, 
  ArrowRight,
  Brain,
  ChevronDown,
  ShieldCheck,
  TrendingUp
} from 'lucide-react';
import { ROUTES } from '../router/routes';

const AIInsightsDesktop = () => {
  const navigate = useNavigate();

  const diagnostics = [
    { icon: <Activity className="text-red-600" />, label: 'Cardiovascular', risk: 'High Risk', riskColor: 'bg-red-100 text-red-700', value: '78%', trend: '+4% MoM', trendColor: 'text-red-500', bgColor: 'bg-red-50' },
    { icon: <FlaskConical className="text-amber-600" />, label: 'Metabolic System', risk: 'Moderate', riskColor: 'bg-amber-100 text-amber-700', value: '42%', trend: 'Stable', trendColor: 'text-slate-400', bgColor: 'bg-amber-50' },
    { icon: <Brain className="text-blue-600" />, label: 'Neurological', risk: 'Low Risk', riskColor: 'bg-blue-100 text-blue-700', value: '12%', trend: '-2% MoM', trendColor: 'text-blue-500', bgColor: 'bg-blue-50' },
    { icon: <Stethoscope className="text-green-600" />, label: 'Respiratory', risk: 'Minimal', riskColor: 'bg-green-100 text-green-700', value: '08%', trend: 'Optimal', trendColor: 'text-green-500', bgColor: 'bg-green-50' },
  ];

  const confidenceIndices = [
    { label: 'Clinical Data Fidelity', value: 96, color: 'bg-[#6043F4]' },
    { label: 'Predictive Accuracy', value: 91, color: 'bg-[#009CDE]' },
    { label: 'Data Set Convergence', value: 88, color: 'bg-[#13082A]' },
    { label: 'Validation Scoring', value: 94, color: 'bg-[#6043F4]' },
  ];

  const shapImportance = [
    { label: 'Systolic Blood Pressure', impact: '+0.32 Impact', width: '82%', positive: true },
    { label: 'LDL Cholesterol', impact: '+0.24 Impact', width: '65%', positive: true },
    { label: 'BMI (Calculated)', impact: '+0.18 Impact', width: '48%', positive: true },
    { label: 'Physical Activity (Bio-Log)', impact: '-0.09 Negative Correlation', width: '25%', positive: false },
  ];

  const sidebarLinks = [
    { icon: <LayoutDashboard size={20} />, label: 'Overview', path: ROUTES.DASHBOARD },
    { icon: <Activity size={20} />, label: 'Health Insights', path: ROUTES.INSIGHTS, active: true },
    { icon: <Science size={20} />, label: 'Scenario Sim', path: ROUTES.SIMULATOR },
    { icon: <FolderOpen size={20} />, label: 'Patient Records', path: ROUTES.REPORTS },
    { icon: <Settings size={20} />, label: 'Configuration', path: ROUTES.SETTINGS },
  ];

  // Animation variants
  const containerVariants = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { staggerChildren: 0.1 } }
  };

  const itemVariants = {
    initial: { opacity: 0, y: 15 },
    animate: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } }
  };

  return (
    <div className="bg-[#EAEAEA] dark:bg-[#13082A] text-slate-900 dark:text-slate-100 min-h-screen font-display flex overflow-hidden">
      
      {/* Sidebar Navigation - Matched Stitch Research Intel v2.4 */}


      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-y-auto bg-slate-50/50 dark:bg-transparent custom-scrollbar">
        
        {/* Top Navbar - Matched Stitch Breadcrumbs */}
        <header className="h-20 bg-white/80 dark:bg-slate-900/80 border-b border-slate-200 dark:border-white/5 flex items-center justify-between px-8 sticky top-0 z-10 backdrop-blur-md">
          <div className="flex items-center gap-4">
            <span className="text-slate-400 text-sm font-medium">Clinical Dashboard</span>
            <span className="text-slate-300">/</span>
            <span className="text-slate-900 dark:text-white font-bold text-sm">Patient Analysis #PX-8821</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative group hidden md:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6043F4] transition-colors" size={16} />
              <input 
                className="w-full bg-slate-100 dark:bg-slate-800 border-none rounded-xl pl-10 pr-4 py-2 text-sm focus:ring-2 focus:ring-[#6043F4]/20 transition-all font-medium" 
                placeholder="Search insights..." 
                type="text"
              />
            </div>
            <button className="size-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-400 hover:bg-slate-200 transition-colors" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
              <Bell size={20} />
            </button>
            <button className="bg-[#6043F4] text-white px-5 py-2 rounded-xl text-sm font-bold flex items-center gap-2 hover:opacity-90 transition-all shadow-md shadow-[#6043F4]/10">
              <Plus size={16} strokeWidth={3} />
              <span>New Analysis</span>
            </button>
          </div>
        </header>

        <div className="p-8 max-w-[1600px] mx-auto w-full space-y-8">
          
          {/* Header Stats - Diagnostic Overview */}
          <div className="flex flex-col md:flex-row items-start md:items-end justify-between gap-6">
            <div>
              <h2 className="text-4xl font-bold text-slate-900 dark:text-white tracking-tight">Diagnostic Overview</h2>
              <p className="text-slate-500 dark:text-slate-400 mt-2 font-medium">Last synced: 14 mins ago • AI Model v4.1-Stable</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-4 py-2 rounded-xl text-sm font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-50 transition-all flex items-center gap-2">
                <FileText size={16} className="text-slate-400" />
                Generate Report
              </button>
              <button 
                onClick={() => navigate(ROUTES.SIMULATOR)}
                className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-4 py-2 rounded-xl text-sm font-bold text-slate-700 dark:text-slate-200 hover:bg-slate-50 transition-all flex items-center gap-2"
              >
                <Brain size={16} className="text-slate-400" />
                Simulate Scenario
              </button>
              <button className="bg-[#009CDE] text-white px-4 py-2 rounded-xl text-sm font-bold flex items-center gap-2 hover:opacity-90 shadow-lg shadow-[#009CDE]/10 transition-all">
                <Stethoscope size={16} />
                Consult Specialist
              </button>
            </div>
          </div>

          {/* Section 1: Disease Breakdown Matrix */}
          <motion.div 
            variants={containerVariants}
            initial="initial"
            animate="animate"
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"
          >
            {diagnostics.map((diag) => (
              <motion.div 
                key={diag.label} 
                variants={itemVariants}
                className="bg-white dark:bg-slate-900/50 p-6 rounded-2xl shadow-sm border border-slate-100 dark:border-white/5 hover:shadow-md transition-shadow group cursor-pointer"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className={`size-12 rounded-xl ${diag.bgColor} flex items-center justify-center shadow-inner group-hover:scale-110 transition-transform`}>
                    {diag.icon}
                  </div>
                  <span className={`${diag.riskColor} text-[10px] font-bold px-2 py-1 rounded-full uppercase tracking-wider`}>{diag.risk}</span>
                </div>
                <h3 className="text-slate-500 dark:text-slate-400 text-sm font-bold">{diag.label}</h3>
                <div className="flex items-end gap-2 mt-1">
                  <span className="text-3xl font-bold text-slate-900 dark:text-white leading-none">{diag.value}</span>
                  <span className={`${diag.trendColor} text-xs font-bold mb-1`}>{diag.trend}</span>
                </div>
              </motion.div>
            ))}
          </motion.div>

          {/* Section 2: AI Confidence Indices - Clinical Fidelity */}
          <motion.div 
            variants={itemVariants} 
            initial="initial" 
            animate="animate"
            className="bg-white dark:bg-slate-900/50 p-8 rounded-3xl shadow-sm border border-slate-100 dark:border-white/5"
          >
            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-6 flex items-center gap-2">
              <ShieldCheck className="text-[#6043F4]" size={24} />
              AI Confidence Indices
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6">
              {confidenceIndices.map((index) => (
                <div key={index.label} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="font-bold text-slate-700 dark:text-slate-300">{index.label}</span>
                    <span className="font-bold" style={{ color: index.color.includes('6043F4') ? '#6043F4' : index.color.includes('009CDE') ? '#009CDE' : '#13082A' }}>{index.value}%</span>
                  </div>
                  <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden shadow-inner">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${index.value}%` }}
                      transition={{ duration: 1, ease: "easeOut" }}
                      className={`h-full ${index.color} rounded-full`} 
                    ></motion.div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Section 3: AI Clinical Narrative & SHAP Maps */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pb-10">
            
            {/* Left: AI Explanation Panel */}
            <motion.div 
              variants={itemVariants}
              initial="initial"
              animate="animate"
              className="lg:col-span-5 bg-[#13082A] text-slate-200 p-8 rounded-3xl flex flex-col gap-6 relative overflow-hidden group shadow-2xl"
            >
              <div className="absolute top-0 right-0 size-64 bg-[#6043F4]/20 blur-[100px] rounded-full -mr-20 -mt-20 group-hover:scale-150 transition-transform duration-1000"></div>
              <h3 className="text-xl font-bold flex items-center gap-2 relative z-10">
                <MessageSquare className="text-[#009CDE]" size={24} />
                AI Clinical Narrative
              </h3>
              <div className="space-y-4 relative z-10">
                <p className="text-slate-400 leading-relaxed font-medium">
                  Analysis indicates a significant <span className="text-white font-bold underline decoration-[#009CDE] decoration-2 underline-offset-4">Cardiovascular elevation</span> correlated with recent biomarker shifts in Systolic BP (+12%) and LDL levels. 
                </p>
                <div className="bg-slate-800/50 p-5 rounded-2xl border border-slate-700/50 shadow-inner group/rec hover:bg-slate-800 transition-colors">
                  <h4 className="text-[#009CDE] text-xs font-bold uppercase tracking-widest mb-2">Key Recommendation</h4>
                  <p className="text-sm leading-relaxed font-semibold">Immediate titration of Lipitor dosage and 24-hour Holter monitoring suggested. The metabolic system shows resilience, yet early signs of insulin resistance are emerging.</p>
                </div>
                <ul className="space-y-3 pt-2">
                  <li className="flex items-start gap-3 text-sm font-semibold group/item cursor-default">
                    <ShieldCheck className="text-green-500 text-lg group-hover/item:scale-125 transition-transform" size={18} />
                    <span>Neurological signals remain baseline stable.</span>
                  </li>
                  <li className="flex items-start gap-3 text-sm font-semibold text-slate-400 group/item cursor-default">
                    <Activity className="text-amber-500 text-lg group-hover/item:scale-125 transition-transform" size={18} />
                    <span>Next recommended lab work: HbA1c panel.</span>
                  </li>
                </ul>
              </div>
              <button className="mt-auto bg-slate-800 text-white w-full py-3 rounded-xl text-sm font-bold border border-slate-700 hover:bg-slate-700 hover:shadow-lg transition-all active:scale-[0.98] z-10">
                Ask Follow-up Question
              </button>
            </motion.div>

            {/* Right: Feature Importance Panel - SHAP Map */}
            <motion.div 
              variants={itemVariants}
              initial="initial"
              animate="animate"
              className="lg:col-span-7 bg-white dark:bg-slate-900/50 p-8 rounded-3xl shadow-sm border border-slate-100 dark:border-white/5"
            >
              <div className="flex justify-between items-center mb-8">
                <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <TrendingUp className="text-[#6043F4]" size={24} />
                  SHAP Feature Importance
                </h3>
                <div className="flex gap-2 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
                  <button className="text-xs font-bold text-[#6043F4] px-3 py-1 bg-white dark:bg-slate-700 rounded shadow-sm">Impact Score</button>
                  <button className="text-xs font-bold text-slate-400 px-3 py-1 hover:bg-white/50 dark:hover:bg-slate-700 transition-all rounded">Raw Values</button>
                </div>
              </div>
              
              <div className="space-y-8">
                {shapImportance.map((item, i) => (
                  <div key={item.label} className="space-y-2 group/bar">
                    <div className="flex justify-between text-xs font-bold uppercase tracking-tight text-slate-500">
                      <span className="group-hover/bar:text-[#6043F4] transition-colors">{item.label}</span>
                      <span className="text-slate-900 dark:text-white">{item.impact}</span>
                    </div>
                    <div className="h-6 w-full bg-slate-50 dark:bg-slate-800/30 rounded-lg overflow-hidden flex relative shadow-inner">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: item.width }}
                        transition={{ duration: 1, delay: i * 0.1 }}
                        className={`h-full ${item.positive ? 'bg-gradient-to-r from-[#6043F4] to-[#009CDE] rounded-r-lg' : 'bg-[#009CDE] rounded-l-lg'} opacity-90 transition-opacity group-hover/bar:opacity-100`} 
                        style={{ marginLeft: item.positive ? '0' : 'auto' }}
                      ></motion.div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-8 pt-6 border-t border-slate-100 dark:border-white/5 flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-400 font-bold uppercase tracking-wider gap-4">
                <p>Global Importance: Based on 500k+ reference clinical trials.</p>
                <button className="text-[#6043F4] hover:underline flex items-center gap-1 group">
                  View All Features
                  <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </motion.div>

          </div>
        </div>
        
        {/* Footer Meta - Confidential Medical Record */}
        <footer className="mt-auto px-8 py-6 border-t border-slate-200 dark:border-white/5 bg-white/50 dark:bg-slate-900/50 text-slate-400 text-xs flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="font-medium text-[10px] uppercase tracking-widest">© 2024 ArogyaAI Intelligence Systems. Confidential Medical Record #PX-8821.</p>
          <div className="flex gap-6 font-bold text-[10px] uppercase tracking-widest">
            <a className="hover:text-[#6043F4] transition-colors" href="#">HIPAA Compliance</a>
            <a className="hover:text-[#6043F4] transition-colors" href="#">Privacy Shield</a>
            <a className="hover:text-[#6043F4] transition-colors" href="#">Data Export</a>
          </div>
        </footer>
      </main>

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(96, 67, 244, 0.1); border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(96, 67, 244, 0.2); }
      `}} />
    </div>
  );
};

export default AIInsightsDesktop;

