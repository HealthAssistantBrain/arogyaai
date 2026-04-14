import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import { 
import { openCommandPalette } from '../components/CommandPalette';
  LayoutDashboard, 
  Brain, 
  Search, 
  Activity, 
  List, 
  FlaskConical, 
  FileText, 
  Moon, 
  Smartphone, 
  Bell, 
  Sparkles, 
  Settings, 
  LifeBuoy, 
  Search as SearchIcon, 
  Rocket, 
  Zap, 
  Info, 
  Download,
  Share2,
  ChevronRight,
  ShieldCheck,
  ChevronDown
} from 'lucide-react';

const WhatsNew = () => {
  const navigate = useNavigate();

  const menuItems = [
    { icon: <LayoutDashboard size={20} />, label: 'Dashboard', path: ROUTES.DASHBOARD },
    { icon: <Brain size={20} />, label: 'AI Insights', path: ROUTES.INSIGHTS },
    { icon: <SearchIcon onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} size={20} />, label: 'Disease Simulator', path: '/simulator' },
    { icon: <Activity size={20} />, label: 'Health List', path: ROUTES.List },
    { icon: <FlaskConical size={20} />, label: 'Lab Results', path: ROUTES.LAB_RESULTS },
    { icon: <FileText size={20} />, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS },
    { icon: <Moon size={20} />, label: 'Sleep Analysis', path: ROUTES.SLEEP },
    { icon: <Smartphone size={20} />, label: 'Device Manager', path: '/device-manager' },
    { icon: <Bell size={20} />, label: 'Notifications', path: ROUTES.NOTIFICATIONS },
    { icon: <Sparkles size={20} />, label: "What's New", path: ROUTES.WHATS_NEW, active: true },
    { icon: <Settings size={20} />, label: 'Settings', path: ROUTES.SETTINGS },
    { icon: <LifeBuoy size={20} />, label: 'Help Center', path: ROUTES.HELP },
  ];

  return (
    <div className="bg-[#EAEAEA] dark:bg-[#13082A] text-[#13082A] font-display min-h-screen flex h-screen overflow-hidden antialiased transition-colors duration-500">
      {/* Sidebar */}


      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative z-10 bg-[#F6F6F6] dark:bg-[#0F0D19]">
        {/* Header */}
        <header className="bg-white/80 dark:bg-[#13082A]/80 backdrop-blur-2xl border-b border-slate-200 dark:border-white/5 h-24 px-10 flex items-center justify-between shrink-0 sticky top-0 z-50">
          <div className="flex-1 max-w-2xl relative">
            <div className="relative group">
              <Search onClick={openCommandPalette} style={{ cursor: "pointer", pointerEvents: "auto" }} className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-[#6143f4] transition-colors" size={18} />
              <input 
                className="w-full pl-16 pr-6 py-4 bg-slate-100/50 dark:bg-white/5 border-none rounded-2xl focus:outline-none focus:ring-4 focus:ring-[#6143f4]/10 transition-all text-[11px] font-bold text-[#13082A] dark:text-white uppercase tracking-[0.2em] italic placeholder:text-slate-400" 
                placeholder="Search updates, protocols or features..." 
                type="text"
              />
            </div>
          </div>
          <div className="flex items-center gap-8 pl-10">
            <div className="flex items-center gap-3">
              <button className="relative p-3.5 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] dark:hover:bg-white/5 rounded-2xl transition-all group" type="button" onClick={() => navigate(ROUTES.NOTIFICATIONS)}>
                <Bell size={20} strokeWidth={2.5} />
                <span className="absolute top-3.5 right-3.5 w-2.5 h-2.5 bg-red-500 rounded-full ring-2 ring-white dark:ring-[#13082A] animate-pulse"></span>
              </button>
            </div>
            <div className="h-10 w-px bg-slate-200 dark:bg-white/10"></div>
            <div className="flex items-center gap-4 cursor-pointer group">
               <div className="text-right hidden xl:block">
                <p className="text-[10px] font-black text-[#13082A] dark:text-white uppercase tracking-widest leading-none mb-1 group-hover:text-[#6143f4] transition-colors italic">Elena Smith</p>
                <p className="text-[9px] font-black text-[#009CDE] uppercase tracking-widest leading-none opacity-80 italic">Verified Node</p>
              </div>
              <div className="relative size-12 transform group-hover:scale-105 transition-all duration-300">
                <div className="absolute inset-0 bg-gradient-to-tr from-[#6143f4] to-[#009CDE] rounded-2xl blur-md opacity-0 group-hover:opacity-40 transition-opacity"></div>
                <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuA3Bdli7Qdd69ZkJQoWmQ0ix2YhA5GXiazo1huJuC-WOj_rqlZqTY62oootlelD1jPdsnS_G-5LAj9unkPs76nczKSVJxv4flOsfxSH8JqPZ3jndQeDtSpzKngHGu5qxWihbOzPO4xvk9zScxUsp7WUNC-SqRji1gdDnK6rRO-5IO7rQu2jHkW2yO16PwfzU80U9jvBGSSsnJV1ev6SBude2H6OGhNuyiJC4WC14KOdMlSDLOQVdazk5lFg2e71qTIQC3BhLeBbZQRp" alt="Admin" className="size-full object-cover rounded-2xl border-2 border-white dark:border-white/10 shadow-lg relative z-10" />
              </div>
            </div>
          </div>
        </header>

        {/* Scrollable Area */}
        <section className="flex-1 overflow-y-auto p-12 custom-scrollbar">
          <div className="max-w-6xl mx-auto space-y-16 pb-24">
            
            {/* Page Header Hero */}
            <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-12">
              <motion.div initial={{ x: -20, opacity: 0 }} animate={{ x: 0, opacity: 1 }}>
                <h2 className="text-7xl font-black text-[#13082A] dark:text-white tracking-tighter uppercase leading-[0.8] mb-6 italic">What's <span className="text-[#6143f4]">New</span></h2>
                <p className="text-sm font-black text-slate-500 dark:text-slate-400 uppercase tracking-[0.2em] italic max-w-xl">Discover the latest updates and health intelligence capabilities deployed to the network.</p>
              </motion.div>
              <div className="flex flex-wrap gap-6 shrink-0">
                <button className="px-14 py-7 bg-[#6143f4] text-white text-[11px] font-black uppercase tracking-[0.5em] rounded-[2rem] shadow-3xl shadow-[#6143f4]/30 hover:-translate-y-2 hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-6 italic group">
                  Explore Features <Rocket size={20} className="group-hover:animate-bounce" strokeWidth={3} />
                </button>
                <button onClick={() => navigate(ROUTES.DASHBOARD)} className="px-14 py-7 bg-white dark:bg-white/5 text-[11px] font-black text-[#13082A] dark:text-white uppercase tracking-[0.5em] rounded-[2rem] border border-slate-200 dark:border-white/10 hover:bg-slate-50 dark:hover:bg-white/10 transition-all italic">
                  Dismiss
                </button>
              </div>
            </div>

            {/* Featured Release Gradient Card */}
            <motion.div 
              initial={{ y: 30, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="bg-white dark:bg-slate-900 rounded-[4rem] overflow-hidden border border-slate-100 dark:border-white/5 shadow-3xl shadow-[#6143f4]/5 group relative"
            >
              <div className="h-96 bg-gradient-to-br from-[#6143f4] via-[#6143f4] to-[#009CDE] p-20 relative flex items-center overflow-hidden">
                <div className="relative z-10 text-white max-w-3xl space-y-8">
                  <div className="inline-block px-8 py-3 bg-white/20 backdrop-blur-2xl rounded-full text-[10px] font-black uppercase tracking-[0.5em] border border-white/20 italic">Current Intelligence Node</div>
                  <h3 className="text-9xl font-black tracking-tighter leading-none italic">v2.4.0</h3>
                  <p className="text-2xl font-black text-white/90 leading-tight max-w-2xl uppercase tracking-tighter italic">Introducing real-time biometric synchronization and enhanced predictive pathology modeling.</p>
                </div>
                {/* Abstract Visual Pattern */}
                <div className="absolute right-[-10%] top-[-10%] size-[800px] opacity-10 pointer-events-none transform rotate-12 group-hover:scale-110 transition-transform duration-1000 grayscale select-none">
                  <img src="https://lh3.googleusercontent.com/aida-public/AB6AXuBkEWclbFk7wXxeBoFyb7yh7t2Du9GoKDk0CoNqgf1-4roUxLiBHPc-TgqpjUIiLPNGaf8ENU9UDs1zWCGMnpny22IYVOlMODiXf_Tr0fIsyUAWa_SjfsjfuAIyn-vdUniAMj2zLzM3hFS7HGVe4frIHIZMlHjFaddnA-ecH3JKEpYAbmM-4TvOayFSCsjQ2Fy7RDNEmAkfl_05GFatyEKDjlvaFql1FhvUSKb-AHoUqjDBfayGh4kEFCkrkkx0nLlv9pVqAlpyrEI8" alt="" className="size-full object-cover" />
                </div>
                <div className="absolute -left-20 -bottom-20 w-[600px] h-[600px] bg-white/10 rounded-full blur-[160px] animate-pulse"></div>
              </div>

              <div className="p-20 space-y-16">
                <div className="space-y-10 relative">
                  <h4 className="text-3xl font-black text-[#13082A] dark:text-white flex items-center gap-8 uppercase tracking-tighter italic">
                    <div className="bg-[#6143f4] size-14 rounded-2xl flex items-center justify-center text-white shadow-2xl shadow-[#6143f4]/20 transform -rotate-3 group-hover:rotate-0 transition-transform">
                      <Zap size={32} strokeWidth={2.5} />
                    </div>
                    Major Protocol Overhaul
                  </h4>
                  <p className="text-lg font-bold text-slate-500 dark:text-slate-400 leading-relaxed uppercase tracking-tight italic max-w-4xl">
                    The 2.4.0 release represents a quantum leap in predictive diagnostics. We've overhauled our simulation engine to account for multi-variable environmental factors and improved sync latency for wearable devices by 40%.
                  </p>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                  {[
                    { label: 'Real-time Biometrics', sub: 'Instant processing of heart rate variability and SpO2 trends with zero-lag synchronization.', color: 'from-[#6143f4] to-[#009CDE]' },
                    { label: 'Stability & Performance', sub: 'Optimized report generation pipelines for high-density diagnostic data streams across all regions.', color: 'from-[#009CDE] to-cyan-500' }
                  ].map((item, i) => (
                    <div key={i} className="p-12 rounded-[3.5rem] bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/5 group/item hover:border-[#6143f4]/30 hover:bg-white dark:hover:bg-slate-800 transition-all duration-500 hover:shadow-2xl hover:shadow-[#6143f4]/5">
                      <div className={`size-1.5 rounded-full bg-gradient-to-r ${item.color} mb-8 shadow-[0_0_12px_#6143f4]`}></div>
                      <p className="text-xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter mb-4 italic leading-none">{item.label}</p>
                      <p className="text-[11px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest leading-relaxed italic opacity-80">{item.sub}</p>
                    </div>
                  ))}
                </div>
              </div>
            </motion.div>

            {/* Feature Highlights Grid */}
            <div className="space-y-12 pt-12">
              <h3 className="text-4xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic flex items-center gap-6">
                 New Capabilities
                 <div className="h-px flex-1 bg-slate-200 dark:bg-white/10 opacity-60"></div>
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                {[
                  { icon: <Activity size={32} />, label: 'Enhanced Disease Simulation', sub: 'Model complex disease trajectories using our new stochastic simulation engine. Supports over 400+ distinct pathological markers with 99.2% inference accuracy.' },
                  { icon: <Share2 size={32} />, label: 'Biometric Data Export', sub: 'Seamlessly export your raw biometric data into HL7 FHIR or PDF formats for easy review within the Arogya medical ecosystem.' }
                ].map((item, i) => (
                  <motion.div 
                    whileHover={{ y: -10 }}
                    key={i} 
                    className="bg-white dark:bg-white/5 p-16 rounded-[4rem] border border-slate-100 dark:border-white/5 shadow-3xl shadow-[#6143f4]/5 hover:border-[#6143f4]/30 transition-all group"
                  >
                    <div className="size-20 rounded-[1.5rem] bg-[#009CDE]/10 text-[#009CDE] flex items-center justify-center mb-10 group-hover:bg-[#009CDE] group-hover:text-white transition-all duration-500 shadow-inner group-hover:shadow-[0_0_30px_#009CDE]/40">
                      {item.icon}
                    </div>
                    <h4 className="text-2xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter leading-none mb-6 group-hover:text-[#009CDE] transition-colors italic">{item.label}</h4>
                    <p className="text-[13px] font-bold text-slate-500 dark:text-slate-400 leading-relaxed uppercase tracking-tight italic opacity-80">{item.sub}</p>
                    <div className="mt-10 pt-10 border-t border-slate-50 dark:border-white/5 italic flex items-center gap-3 text-[10px] font-black uppercase text-[#009CDE] tracking-widest opacity-0 group-hover:opacity-100 transition-opacity">
                      Learn More <ChevronRight size={14} strokeWidth={3} />
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Version History Log */}
            <div className="space-y-12 pt-12">
              <h3 className="text-4xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic flex items-center gap-6">
                 Version Archive
                 <div className="h-px flex-1 bg-slate-200 dark:bg-white/10 opacity-60"></div>
              </h3>
              <div className="space-y-10">
                {[
                  { ver: '2.3.5', date: 'Nov 12, 2026', title: 'Performance & Wearable Patch', items: ['Improved battery efficiency for background device synchronization on iOS/Android.', 'Fixed a bug where sleep latency wasn\'t correctly calculated for fragmented rest.', 'Added localized support for French, German, and Japanese medical reports.'] },
                  { ver: '2.3.0', date: 'Oct 28, 2026', title: 'AI Forecasting Foundations', items: ['Integration with Apple HealthKit and Google Fit 2.0 specialized APIs.', 'Redesigned \'Health List\' view with 3D visualization capabilities.', 'Security hardening for biometric data encryption at rest (AES-256).'] }
                ].map((log, i) => (
                  <motion.div 
                    initial={{ opacity: 0 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ once: true }}
                    key={i} 
                    className="bg-white dark:bg-white/5 p-16 rounded-[4rem] border border-slate-100 dark:border-white/5 group overflow-hidden relative"
                  >
                    <div className="flex flex-col xl:flex-row xl:items-start justify-between gap-12 mb-12 relative z-10">
                      <div className="space-y-4">
                        <div className="flex items-center gap-8">
                          <h4 className="text-3xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic leading-none">Version {log.ver}</h4>
                          <span className="px-6 py-2 bg-slate-100 dark:bg-white/5 rounded-full text-[10px] font-black uppercase text-slate-500 tracking-[0.2em] italic border border-slate-200/50">{log.date}</span>
                        </div>
                        <p className="text-sm font-black text-[#6143f4] uppercase tracking-[0.4em] italic leading-none">{log.title}</p>
                      </div>
                      <button className="text-slate-300 hover:text-[#6143f4] transition-all transform hover:rotate-90">
                        <Info size={32} strokeWidth={2.5} className="opacity-40 group-hover:opacity-100" />
                      </button>
                    </div>
                    <ul className="space-y-6 relative z-10">
                      {log.items.map((item, j) => (
                        <li key={j} className="flex items-start gap-8 group/li">
                          <div className="size-3 rounded-full bg-[#009CDE] mt-1.5 shrink-0 shadow-[0_0_15px_#009CDE]/50 transform transition-transform group-hover/li:scale-125"></div>
                          <p className="text-[12px] font-black text-slate-500 dark:text-slate-400 uppercase tracking-tight italic leading-relaxed opacity-80 group-hover/li:opacity-100 transition-opacity">{item}</p>
                        </li>
                      ))}
                    </ul>
                    <div className="absolute right-[-5%] bottom-[-5%] size-64 bg-slate-100 dark:bg-white/5 rounded-full blur-[100px] opacity-0 group-hover:opacity-100 transition-opacity duration-1000"></div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Premium Join Beta CTA */}
            <motion.div 
              whileHover={{ scale: 1.01 }}
              className="bg-[#6143f4]/5 dark:bg-[#6143f4]/10 rounded-[5rem] p-24 border-2 border-dashed border-[#6143f4]/20 text-center space-y-12 shadow-3xl shadow-[#6143f4]/5 relative overflow-hidden group"
            >
              <div className="space-y-6 relative z-10">
                <div className="bg-[#6143f4] size-20 rounded-[2.5rem] flex items-center justify-center text-white shadow-2xl shadow-[#6143f4]/30 mx-auto mb-10 group-hover:scale-110 transition-transform">
                  <ShieldCheck size={40} strokeWidth={2.5} />
                </div>
                <h5 className="text-5xl font-black text-[#13082A] dark:text-white uppercase tracking-tighter italic leading-none">Shape the Future of ArogyaAI</h5>
                <p className="text-sm font-black text-slate-500 dark:text-slate-400 uppercase tracking-[0.3em] max-w-2xl mx-auto italic leading-relaxed opacity-80">
                  Join our early access beta program to test upcoming clinical intelligence tools and edge protocols before they launch on the global node network.
                </p>
              </div>
              <button className="px-16 py-8 bg-[#6143f4] text-white text-[11px] font-black uppercase tracking-[0.5em] rounded-[2.5rem] shadow-3xl shadow-[#6143f4]/30 hover:shadow-[#6143f4]/50 hover:-translate-y-2 active:scale-95 transition-all italic relative z-10 overflow-hidden group/btn">
                <span className="relative z-10">Join Beta Protocol</span>
                <div className="absolute inset-0 bg-white/10 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700 italic"></div>
              </button>
              {/* Decorative elements */}
              <div className="absolute -left-20 -top-20 size-80 bg-[#6143f4]/10 rounded-full blur-[120px] group-hover:scale-150 transition-transform duration-1000"></div>
              <div className="absolute -right-20 -bottom-20 size-80 bg-[#009CDE]/10 rounded-full blur-[120px] group-hover:scale-150 transition-transform duration-1000"></div>
            </motion.div>

            {/* Standardized Branding Footer */}
            <footer className="pt-24 border-t border-slate-200 dark:border-white/5 opacity-40 hover:opacity-100 transition-all duration-700">
              <div className="flex flex-col md:flex-row justify-between items-center gap-12">
                <div className="flex items-center gap-4 group">
                  <div className="size-10 rounded-xl bg-slate-300 dark:bg-white/10 flex items-center justify-center group-hover:bg-[#6143f4] transition-colors">
                    <Activity size={20} className="text-white" strokeWidth={3} />
                  </div>
                  <span className="text-2xl font-black text-slate-500 uppercase tracking-tighter group-hover:text-[#13082A] dark:group-hover:text-white transition-colors">Arogya<span className="text-slate-400">AI</span></span>
                </div>
                <div className="flex flex-wrap justify-center gap-12 font-black uppercase tracking-[0.4em] italic text-[10px]">
                  {['Legal', 'Privacy', 'Network Status', 'Compliance'].map(l => (
                    <a key={l} href="#" className="hover:text-[#6143f4] transition-colors">{l}</a>
                  ))}
                </div>
                <div className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] italic">© 2026 ArogyaAI Systems. Global Monitoring.</div>
              </div>
            </footer>

          </div>
        </section>
      </main>

      <style dangerouslySetInnerHTML={{ __html: `
        .custom-scrollbar::-webkit-scrollbar { width: 8px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; border: 2px solid transparent; background-clip: content-box; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); border: 2px solid transparent; background-clip: content-box; }
        
        @keyframes bounce-slow {
          0%, 100% { transform: translateY(-5%); animation-timing-function: cubic-bezier(0.8, 0, 1, 1); }
          50% { transform: translateY(0); animation-timing-function: cubic-bezier(0, 0, 0.2, 1); }
        }
        .animate-bounce-slow { animation: bounce-slow 2s infinite; }
      `}} />
    </div>
  );
};

export default WhatsNew;

