import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  LayoutDashboard, 
  Brain, 
  Activity, 
  TrendingUp, 
  Settings, 
  Search, 
  Bell, 
  Sliders, 
  Stethoscope, 
  Plus, 
  ArrowRight,
  ChevronDown,
  Info,
  CheckCircle2
} from 'lucide-react';
import { ROUTES } from '../router/routes';

const Simulate = () => {
  const navigate = useNavigate();
  const [isSimulating, setIsSimulating] = useState(false);
  const [progress, setProgress] = useState(65);
  const [selectedPeriod, setSelectedPeriod] = useState('6 Months');
  
  // Simulation state
  const [params, setParams] = useState({
    sleep: 7.5,
    steps: 8400,
    weight: 72,
    stress: 4,
    exercise: 3.5
  });

  const runSimulation = () => {
    setIsSimulating(true);
    // Pulse effect simulation logic
    setTimeout(() => {
      setIsSimulating(false);
      setProgress(Math.min(100, progress + 5));
    }, 2000);
  };

  const riskComparison = [
    { label: 'Cardiovascular', current: '12.4%', simulated: '7.2%', currentWidth: '60%', simulatedWidth: '35%' },
    { label: 'Diabetes (Type II)', current: '8.1%', simulated: '4.0%', currentWidth: '45%', simulatedWidth: '20%' },
    { label: 'Respiratory', current: '3.2%', simulated: '2.1%', currentWidth: '25%', simulatedWidth: '18%' },
  ];

  const sidebarLinks = [
    { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD },
    { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS },
    { icon: Sliders, label: 'Disease Simulator', path: ROUTES.SIMULATOR, active: true },
    { icon: Activity, label: 'Health Timeline', path: ROUTES.TIMELINE },
    { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS },
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
    <div className="bg-[#EAEAEA] dark:bg-[#13082A] text-slate-900 dark:text-slate-100 min-h-screen font-display flex overflow-hidden antialiased">
      
      {/* Sidebar Navigation - Matched Stitch */}


      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-y-auto bg-mesh custom-scrollbar">
        
        {/* Top Header Navbar - Matched Stitch */}
        <header className="h-16 flex items-center justify-between px-8 bg-white/80 dark:bg-[#1C1136]/80 backdrop-blur-md sticky top-0 z-30 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center w-full max-w-md">
            <div className="relative w-full group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6043F4] transition-colors" size={16} />
              <input 
                className="w-full bg-slate-100 dark:bg-white/5 border-none rounded-xl pl-10 pr-4 py-2 focus:ring-2 focus:ring-[#6043F4]/20 text-sm font-medium transition-all outline-none" 
                placeholder="Search insights, diseases, or metrics..." 
                type="text"
              />
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            <button className="relative p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-white/5 rounded-full transition-all group active:scale-90">
              <Bell size={20} className="group-hover:text-[#6043F4] transition-colors" />
              <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white dark:border-[#1C1136]"></span>
            </button>
            <div className="h-8 w-[1px] bg-slate-200 dark:bg-slate-700 mx-2"></div>
            <div className="flex items-center gap-3 cursor-pointer group" onClick={() => navigate(ROUTES.SETTINGS)}>
              <div className="text-right hidden sm:block">
                <p className="text-sm font-bold leading-tight group-hover:text-[#6043F4] transition-colors">Dr. Sarah Chen</p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-bold tracking-widest">Premium Member</p>
              </div>
              <div 
                className="w-10 h-10 rounded-full bg-slate-200 bg-cover bg-center border-2 border-[#6043F4] shadow-md transition-transform group-hover:scale-110" 
                style={{ backgroundImage: "url('https://lh3.googleusercontent.com/aida-public/AB6AXuAI3qslKyRggW9CjuiMeglXHlPwdMLM-7k2twF6qYrToVBPJBPEV6kBsJJQKjUNXhBe2Xd8IVlYGBghJhNfZwsCoF9Xl6c2Tbd_SQnKHie09nic4ERnV3YamDU5ZMGKLMm7c4ISiZkgzTJ2jqPp7U1vHuIIQ2SgOrQ8bfRZR4HQ_G2PW8MkusFhzjOnxQYL7IsU9beXky9Nxq-FEeGF2f9oNaYeh_E0mN2LaecpjgE-62RGvQPX7Rlz3slttt9_AbjUYvY_ZhuxT8d9')" }}
              ></div>
            </div>
          </div>
        </header>

        <div className="p-8 max-w-[1400px] mx-auto w-full space-y-8">
          
          {/* Page Header & Period Selector */}
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="w-full">
              <h2 className="text-3xl font-black tracking-tight text-slate-900 dark:text-white">Disease Simulator</h2>
              <p className="text-slate-500 dark:text-slate-400 mt-1 font-medium italic">Adjust lifestyle variables to predict future clinical outcomes with AI modeling.</p>
            </div>
            <div className="flex bg-white dark:bg-[#1C1136] p-1 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 shrink-0">
              {['1 Month', '3 Months', '6 Months', '12 Months'].map((period) => (
                <button 
                  key={period}
                  onClick={() => setSelectedPeriod(period)}
                  className={`px-4 py-2 text-sm font-bold rounded-lg transition-all duration-300 ${
                    period === selectedPeriod 
                    ? 'bg-[#6043F4] text-white shadow-md' 
                    : 'text-slate-500 dark:text-slate-400 hover:text-[#6043F4]'
                  }`}
                >
                  {period}
                </button>
              ))}
            </div>
          </div>

          <motion.div 
            variants={containerVariants}
            initial="initial"
            animate="animate"
            className="grid grid-cols-12 gap-6"
          >
            {/* Left Column: Control Panel & Hero Card */}
            <div className="col-span-12 lg:col-span-4 space-y-6">
              
              {/* Lifestyle Parameters Card */}
              <motion.div 
                variants={itemVariants}
                className="bg-white dark:bg-[#1C1136] p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800"
              >
                <h3 className="font-bold text-lg mb-6 flex items-center gap-2 text-slate-800 dark:text-white">
                  <Sliders className="text-[#6043F4]" size={20} />
                  Lifestyle Parameters
                </h3>
                <div className="space-y-6">
                  {[
                    { key: 'sleep', label: 'Sleep', unit: 'hrs', value: params.sleep, min: 4, max: 12, step: 0.5 },
                    { key: 'steps', label: 'Daily Steps', unit: '', value: params.steps, min: 2000, max: 20000, step: 100 },
                    { key: 'weight', label: 'Weight', unit: 'kg', value: params.weight, min: 40, max: 150, step: 1 },
                    { key: 'stress', label: 'Stress Level', unit: '/ 10', value: params.stress, min: 1, max: 10, step: 1 },
                    { key: 'exercise', label: 'Weekly Exercise', unit: 'hrs', value: params.exercise, min: 0, max: 20, step: 0.5 },
                  ].map((param) => (
                    <div key={param.key} className="group">
                      <div className="flex justify-between mb-2">
                        <label className="text-sm font-bold text-slate-600 dark:text-slate-300 group-hover:text-[#6043F4] transition-colors">{param.label}</label>
                        <span className="text-sm font-black text-[#6043F4]">{param.value.toLocaleString()} {param.unit}</span>
                      </div>
                      <input 
                        className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-[#6043F4] custom-slider" 
                        type="range"
                        min={param.min}
                        max={param.max}
                        step={param.step}
                        value={param.value}
                        onChange={(e) => setParams({...params, [param.key]: parseFloat(e.target.value)})}
                      />
                    </div>
                  ))}
                </div>
                <button 
                  onClick={runSimulation}
                  disabled={isSimulating}
                  className="w-full mt-8 py-3 bg-[#6043F4]/10 dark:bg-[#6043F4]/20 text-[#6043F4] font-bold rounded-xl hover:bg-[#6043F4] hover:text-white transition-all active:scale-[0.98] disabled:opacity-50"
                >
                  {isSimulating ? 'Processing Models...' : 'Run Simulation'}
                </button>
              </motion.div>

              {/* Projected Trajectory Gradient Card */}
              <motion.div 
                variants={itemVariants}
                className="bg-gradient-to-br from-[#6043F4] to-[#6043F4]/80 p-6 rounded-xl shadow-xl text-white relative overflow-hidden group"
              >
                <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:rotate-12 transition-transform duration-700">
                  <TrendingUp size={80} strokeWidth={2.5} />
                </div>
                <div className="relative z-10">
                  <div className="flex justify-between items-start mb-4">
                    <h3 className="font-bold text-lg">Projected Trajectory</h3>
                    <span className="bg-white/20 backdrop-blur-md px-2 py-1 rounded text-xs font-bold uppercase tracking-widest border border-white/20">Live Model</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <motion.div 
                      key={isSimulating}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="text-5xl font-black"
                    >
                      {isSimulating ? '...' : '+14%'}
                    </motion.div>
                    <div className="text-sm leading-tight opacity-90 font-bold uppercase tracking-tighter">Overall Health<br/>Optimization</div>
                  </div>
                  <div className="mt-6 h-2 w-full bg-white/20 rounded-full overflow-hidden shadow-inner">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 1.5, ease: "easeOut" }}
                      className="h-full bg-white rounded-full shadow-[0_0_15px_rgba(255,255,255,0.6)]"
                    ></motion.div>
                  </div>
                  <p className="mt-3 text-xs opacity-80 font-semibold italic">Predicted longevity increase: <span className="text-white font-black underline underline-offset-4 decoration-white/30">2.4 years</span></p>
                </div>
              </motion.div>
            </div>

            {/* Right Column: Comparative Analysis & Logic */}
            <div className="col-span-12 lg:col-span-8 space-y-6">
              
              {/* Risk Comparison Matrix */}
              <motion.div 
                variants={itemVariants}
                className="bg-white dark:bg-[#1C1136] p-8 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800"
              >
                <h3 className="font-bold text-lg mb-8 flex items-center gap-2 text-slate-800 dark:text-white">
                  <Activity className="text-[#009CDE]" size={20} />
                  Risk Comparison: Before vs. After Simulation
                </h3>
                <div className="space-y-8">
                  {riskComparison.map((risk) => (
                    <div key={risk.label} className="grid grid-cols-12 gap-4 items-center group">
                      <div className="col-span-12 md:col-span-3 text-sm font-black text-slate-500 group-hover:text-[#6043F4] transition-colors uppercase tracking-tight">{risk.label}</div>
                      <div className="col-span-12 md:col-span-9 space-y-3">
                        <div className="relative h-10 bg-slate-100 dark:bg-white/5 rounded-xl overflow-hidden flex items-center shadow-inner">
                          <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: risk.currentWidth }}
                            transition={{ duration: 1, delay: 0.5 }}
                            className="h-full bg-slate-300 dark:bg-slate-600 flex items-center px-4 transition-all"
                          >
                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-700 dark:text-slate-300 whitespace-nowrap">Current Risk</span>
                          </motion.div>
                          <span className="ml-auto mr-4 text-sm font-black text-slate-600">{risk.current}</span>
                        </div>
                        <div className="relative h-10 bg-slate-100 dark:bg-white/5 rounded-xl overflow-hidden flex items-center shadow-inner">
                          <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: isSimulating ? '10%' : risk.simulatedWidth }}
                            transition={{ duration: 1, ease: "easeOut" }}
                            className={`h-full bg-[#6043F4]/40 flex items-center px-4 transition-all ${isSimulating ? 'animate-pulse' : ''}`}
                          >
                            <span className="text-[10px] font-black uppercase tracking-widest text-[#6043F4] whitespace-nowrap italic">Simulated Risk</span>
                          </motion.div>
                          <span className="ml-auto mr-4 text-sm font-black text-[#6043F4]">{isSimulating ? '...' : risk.simulated}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* AI Logic Panel */}
              <motion.div 
                variants={itemVariants}
                className="bg-white dark:bg-[#1C1136] p-8 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 relative group"
              >
                <div className="absolute top-0 right-0 p-6 opacity-5 group-hover:scale-110 transition-transform">
                  <Brain size={120} />
                </div>
                <h3 className="font-bold text-lg mb-6 flex items-center gap-2 text-slate-800 dark:text-white">
                  <Brain className="text-[#6043F4]" size={20} />
                  Scenario Analysis: AI Logic
                </h3>
                <div className="bg-slate-50 dark:bg-white/5 p-6 rounded-xl border-l-4 border-[#6043F4] shadow-inner relative z-10 transition-colors hover:bg-slate-100 dark:hover:bg-white/[0.07]">
                  <p className="text-[15px] leading-relaxed text-slate-700 dark:text-slate-300 italic font-medium">
                    "{isSimulating 
                      ? "Neural inference engines are computing outcomes based on global healthcare datasets..." 
                      : `Based on your simulated lifestyle shifts (reaching ${params.sleep} hrs sleep and ${params.steps.toLocaleString()} steps), the model predicts a significant reduction in systemic inflammation markers. Specifically, your C-Reactive Protein (CRP) levels are projected to drop, directly impacting your cardiovascular risk profile. The reduction in stress level to ${params.stress}/10 further stabilizes heart rate variability indicators.`
                    }"
                  </p>
                </div>
                <div className="mt-8 flex flex-wrap gap-4">
                  {[
                    { label: 'Inflammation Lowered', color: 'bg-green-500' },
                    { label: 'Insulin Response Improved', color: 'bg-green-500' },
                    { label: 'Cortisol Stable', color: 'bg-yellow-500' }
                  ].map((tag) => (
                    <div key={tag.label} className="px-5 py-2.5 bg-slate-100 dark:bg-white/10 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-2 shadow-sm border border-transparent hover:border-[#6043F4]/20 transition-all group">
                      <span className={`w-2 h-2 rounded-full ${tag.color} shadow-lg shadow-${tag.color.split('-')[1]}/50 group-hover:scale-125 transition-transform`}></span>
                      {tag.label}
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Dark Specialist CTA */}
              <motion.div 
                variants={itemVariants}
                className="flex flex-col md:flex-row items-center justify-between p-8 bg-[#13082A] rounded-2xl shadow-xl border border-white/5 group relative overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-[#6043F4]/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div className="flex items-center gap-6 relative z-10 w-full md:w-auto mb-6 md:mb-0">
                  <div className="w-14 h-14 rounded-2xl bg-[#6043F4] flex items-center justify-center text-white shadow-xl shadow-[#6043F4]/20 group-hover:rotate-6 transition-transform">
                    <Stethoscope size={28} />
                  </div>
                  <div>
                    <h4 className="text-white text-xl font-black tracking-tight">Ready to take the next step?</h4>
                    <p className="text-slate-400 text-sm font-bold uppercase tracking-widest mt-1">Review this simulation with our medical board.</p>
                  </div>
                </div>
                <button className="px-10 py-4 bg-[#6043F4] text-white font-black text-xs uppercase tracking-[0.2em] rounded-xl shadow-xl shadow-[#6043F4]/20 hover:scale-[1.05] active:scale-95 transition-all z-10">
                  Consult Specialist
                </button>
              </motion.div>
            </div>

          </motion.div>
        </div>
      </main>

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(96, 67, 244, 0.1); border-radius: 20px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(96, 67, 244, 0.2); }
        .bg-mesh {
          background-image: 
            radial-gradient(at 0% 0%, rgba(96, 67, 244, 0.03) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(0, 156, 222, 0.03) 0px, transparent 50%);
        }
        .custom-slider::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 18px;
          height: 18px;
          background: #6043F4;
          cursor: pointer;
          border-radius: 50%;
          border: 2px solid white;
          box-shadow: 0 4px 10px rgba(96, 67, 244, 0.3);
          transition: all 0.2s ease;
        }
        .custom-slider::-webkit-slider-thumb:hover {
          transform: scale(1.15);
          box-shadow: 0 4px 15px rgba(96, 67, 244, 0.4);
        }
      `}} />
    </div>
  );
};

export default Simulate;
