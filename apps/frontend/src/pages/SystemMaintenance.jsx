import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import { 
  Activity, 
  Wrench, 
  Clock, 
  LifeBuoy, 
  ShieldCheck,
  Bell,
  ChevronDown,
  LayoutDashboard,
  Zap
} from 'lucide-react';

const SystemMaintenance = () => {
  const navigate = useNavigate();

  return (
    <div className="bg-[#EAEAEA] dark:bg-[#13082A] text-[#13082A] font-display min-h-screen flex flex-col antialiased transition-colors duration-500 overflow-hidden h-screen">
      
      {/* Mesh Gradient Background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-0 w-full h-full opacity-30 dark:opacity-20" style={{ background: 'radial-gradient(at 0% 0%, rgba(97, 67, 244, 0.4) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(0, 156, 222, 0.4) 0px, transparent 50%)' }}></div>
      </div>

      <div className="relative flex h-full grow flex-col z-10">
        {/* Standardized Dashboard Header */}
        

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col items-center justify-center p-12">
          <div className="max-w-7xl w-full grid grid-cols-1 lg:grid-cols-2 gap-24 items-center">
            
            {/* Clinical Messaging Side */}
            <motion.div 
              initial={{ x: -30, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8 }}
              className="flex flex-col gap-12"
            >
              <div className="space-y-10">
                <div className="inline-flex items-center gap-4 px-8 py-3 rounded-full bg-[#009CDE]/10 text-[#009CDE] border border-[#009CDE]/20 shadow-inner italic transform -rotate-1">
                  <Wrench size={16} strokeWidth={3} />
                  <span className="text-[11px] font-black uppercase tracking-[0.4em]">Protocol Maintenance Active</span>
                </div>
                <h1 className="text-[#13082A] dark:text-white text-7xl md:text-8xl font-black leading-[0.8] tracking-tighter uppercase italic">
                  System <span className="text-[#6143f4]">Optimization</span> <br className="hidden xl:block" />
                  <span className="text-[#6143f4]">Cycle</span> 2.4.0
                </h1>
                <p className="text-slate-500 dark:text-slate-400 text-xl font-bold leading-relaxed max-w-xl uppercase tracking-tight italic opacity-80 decoration-[#6143f4]/20 underline underline-offset-[12px] decoration-4">
                  We're currently performing scheduled diagnostic maintenance to ensure peak performance of our predictive health engine.
                </p>
              </div>

              {/* Estimated Completion Timeline Card */}
              <motion.div 
                whileHover={{ scale: 1.02, rotate: 1 }}
                className="p-1 bg-gradient-to-br from-[#6143f4]/20 to-[#009CDE]/20 rounded-[3rem] shadow-4xl shadow-[#6143f4]/10 max-w-md"
              >
                <div className="bg-white dark:bg-slate-900 rounded-[2.8rem] flex items-center gap-10 p-10 overflow-hidden relative group">
                  <div className="size-20 bg-[#6143f4]/10 rounded-3xl flex items-center justify-center text-[#6143f4] group-hover:bg-[#6143f4] group-hover:text-white transition-all duration-500 relative z-10">
                    <Clock size={40} strokeWidth={2.5} className="animate-pulse" />
                  </div>
                  <div className="relative z-10">
                    <p className="text-[11px] font-black text-[#6143f4] uppercase tracking-[0.4em] mb-3 italic">Estimated Restoration</p>
                    <p className="text-[#13082A] dark:text-white text-4xl font-black tracking-tighter italic leading-none">04:00 <span className="text-slate-300">AM UTC</span></p>
                  </div>
                  {/* Decorative faint clock in bg */}
                  <Clock size={160} className="absolute -right-10 -bottom-10 opacity-[0.03] rotate-12 group-hover:rotate-45 transition-transform duration-1000" />
                </div>
              </motion.div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-8">
                <button 
                  onClick={() => navigate(ROUTES.HELP)}
                  className="px-14 py-7 bg-[#6143f4] text-white rounded-[2rem] font-black text-xs uppercase tracking-[0.4em] shadow-3xl shadow-[#6143f4]/30 hover:-translate-y-2 hover:shadow-[#6143f4]/50 active:scale-95 transition-all flex items-center justify-center gap-6 italic group"
                >
                  <LifeBuoy size={20} strokeWidth={3} className="group-hover:rotate-12 transition-transform" />
                  Request Assistance
                </button>
                <button 
                  onClick={() => navigate(ROUTES.STATUS)}
                  className="px-14 py-7 bg-white dark:bg-white/5 text-[#13082A] dark:text-white border border-slate-200 dark:border-white/10 rounded-[2rem] font-black text-xs uppercase tracking-[0.4em] hover:bg-slate-50 dark:hover:bg-white/10 active:scale-95 transition-all flex items-center justify-center gap-6 italic group"
                >
                  <Activity size={20} className="text-[#009CDE]" strokeWidth={2.5} />
                  Live Node Status
                </button>
              </div>
            </motion.div>

            {/* Premium Visual Side (Waveform Progress Card) */}
            <motion.div 
              initial={{ x: 30, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.8, delay: 0.2 }}
              className="relative group h-full flex items-center justify-center"
            >
              <div className="absolute inset-0 bg-gradient-to-tr from-[#6143f4]/30 to-[#009CDE]/30 blur-[140px] rounded-full scale-75 group-hover:scale-100 transition-transform duration-1000"></div>
              
              <div className="relative w-full max-w-xl aspect-square bg-[#0c091a] rounded-[5rem] overflow-hidden border-4 border-white/10 shadow-5xl transform rotate-3 group-hover:rotate-0 transition-all duration-1000 flex flex-col">
                {/* Waveform Visualization Area */}
                <div className="flex-1 relative flex items-center justify-center overflow-hidden p-12">
                   {/* Abstract Pulse Waveform Layout (Simulated with Gradient and Animation) */}
                   <div className="w-full h-full relative z-10 flex flex-col justify-center gap-2 opacity-80 group-hover:opacity-100 transition-opacity">
                      {[...Array(12)].map((_, i) => (
                        <motion.div 
                          key={i}
                          animate={{ 
                            width: ['10%', '100%', '10%'],
                            opacity: [0.3, 1, 0.3],
                          }}
                          transition={{ 
                            duration: 3 + Math.random() * 2, 
                            repeat: Infinity, 
                            delay: i * 0.1,
                            ease: "easeInOut"
                          }}
                          className={`h-2 rounded-full bg-gradient-to-r from-transparent via-[#009CDE] to-transparent shadow-[0_0_15px_#009CDE]`}
                          style={{ marginLeft: i % 2 === 0 ? '0' : '20%', marginRight: i % 2 === 0 ? '20%' : '0' }}
                        ></motion.div>
                      ))}
                   </div>
                   
                   {/* Centered Medical Tech Focal Point */}
                   <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
                      <div className="size-48 bg-[#009CDE]/10 rounded-full border border-[#009CDE]/20 flex items-center justify-center backdrop-blur-3xl shadow- inner relative group/focal cursor-pointer">
                         <Activity size={80} className="text-[#009CDE] animate-pulse group-hover/focal:scale-110 transition-transform duration-500" strokeWidth={1} />
                         <div className="absolute inset-0 border-2 border-dashed border-[#009CDE]/30 rounded-full animate-[spin_10s_linear_infinite]"></div>
                      </div>
                   </div>

                   <div className="absolute top-10 right-10 flex flex-col gap-4 text-right opacity-40">
                      <p className="text-[10px] font-black text-white uppercase tracking-widest italic">Node-ID: #PX-9921</p>
                      <p className="text-[10px] font-black text-[#009CDE] uppercase tracking-widest italic">Region: EU-West-02</p>
                   </div>
                </div>

                {/* Integration Progress Module */}
                <div className="h-48 bg-gradient-to-r from-[#6143f4] to-[#009CDE] p-12 relative flex flex-col justify-center">
                  <div className="flex justify-between items-end mb-6">
                    <div>
                      <h4 className="text-2xl font-black text-white uppercase tracking-tighter italic leading-none mb-2">Protocol Hardening</h4>
                      <p className="text-[10px] font-black text-white/70 uppercase tracking-[0.4em] italic leading-none">Engine Optimization Cycle v2.4.0</p>
                    </div>
                    <div className="text-right">
                       <span className="text-4xl font-black text-white italic tracking-tighter leading-none">88%</span>
                    </div>
                  </div>
                  {/* High fidelity progress bar */}
                  <div className="h-4 bg-black/30 rounded-full overflow-hidden p-1 shadow-inner relative">
                    <motion.div 
                      initial={{ width: "0%" }}
                      animate={{ width: "88%" }}
                      transition={{ duration: 2, ease: "easeOut" }}
                      className="h-full bg-white rounded-full relative group/bar"
                    >
                      <div className="absolute -inset-2 bg-white blur-xl opacity-20 group-hover/bar:opacity-40 transition-opacity"></div>
                    </motion.div>
                  </div>
                </div>
              </div>
            </motion.div>

          </div>
        </main>

        {/* Standardized Legal Maintenance Footer */}
        <footer className="footer-clinical h-32 border-t border-slate-200 dark:border-white/5 bg-white/40 dark:bg-white/5 px-10 flex items-center relative z-30">
          <div className="max-w-7xl mx-auto w-full flex flex-col items-center justify-between gap-8 md:flex-row">
            <div className="flex items-center gap-10">
              <div className="flex items-center gap-4 group cursor-help">
                <span className="h-3 w-3 rounded-full bg-[#6143f4] shadow-[0_0_15px_#6143f4] animate-pulse"></span>
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 italic">Network Optimizing: Node 55A/X</span>
                <div className="h-6 w-px bg-slate-300 dark:bg-white/10"></div>
              </div>
              <p className="text-[11px] font-black uppercase tracking-[0.4em] text-slate-400 italic opacity-80 decoration-[#009CDE]/40 underline underline-offset-4 decoration-2">© 2026 ArogyaAI Systems. Global Monitoring.</p>
            </div>
            <div className="flex items-center gap-12 font-black uppercase tracking-[0.4em] italic text-[10px] text-slate-500">
              {['Terms of Protocol', 'Security Policy', 'Node Status'].map(l => (
                  <button key={l} className="hover:text-[#6143f4] transition-colors">{l}</button>
              ))}
            </div>
          </div>
        </footer>

      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        .shadow-5xl {
          box-shadow: 0 50px 120px -30px rgba(13, 9, 26, 0.8), 0 0 40px rgba(97, 67, 244, 0.2);
        }
        .shadow-4xl {
          box-shadow: 0 40px 100px -20px rgba(97,67,244,0.3);
        }
      `}} />
    </div>
  );
};

export default SystemMaintenance;
