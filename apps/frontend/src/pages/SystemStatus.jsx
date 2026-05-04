import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import { openCommandPalette } from '../components/CommandPalette';
import { 
  LayoutDashboard, 
  BarChart3, 
  ShieldCheck, 
  Database, 
  Settings, 
  Search, 
  Bell, 
  HelpCircle, 
  CheckCircle2, 
  History, 
  ArrowUp, 
  Server, 
  Brain, 
  RefreshCw, 
  Zap, 
  LifeBuoy, 
  Clock, 
  Check, 
  Calendar, 
  AlertTriangle, 
  Lock, 
  Mail, 
  Phone,
  Activity
} from 'lucide-react';

const SystemStatus = () => {
  const navigate = useNavigate();

  const services = [
    { icon: <Brain size={24} />, name: 'Core AI Engine', sub: 'Inference & Analysis', status: 'Operational' },
    { icon: <RefreshCw size={24} />, name: 'Data Sync', sub: 'HL7/FHIR Real-time', status: 'Operational' },
    { icon: <Zap size={24} />, name: 'Predictive API', sub: 'Public Endpoints', status: 'Operational' },
    { icon: <LifeBuoy size={24} />, name: 'Help Center', sub: 'Documentation/Support', status: 'Operational' }
  ];

  const incidents = [
    {
      title: 'Minor API Latency - US East Region',
      status: 'Resolved',
      desc: 'Users in North America may have experienced increased response times for radiological image analysis. The issue was traced back to a load balancer misconfiguration.',
      date: 'Oct 24, 2026',
      time: '14:22 - 15:05 UTC',
      active: true
    },
    {
      title: 'Database Maintenance - Global',
      status: 'Resolved',
      desc: 'Scheduled performance optimization for patient record indexing. No downtime occurred during this window.',
      date: 'Oct 19, 2026',
      time: '01:00 - 03:00 UTC',
      active: false
    }
  ];

  return (
    <div className="bg-[#EAEAEA] dark:bg-card text-text-primary font-display min-h-screen flex h-screen overflow-hidden antialiased transition-colors duration-500">
      {/* Sidebar */}


      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative z-10 bg-[#F6F6F6] dark:bg-[#0F0D19]">
        {/* Header */}
        

        {/* Scrollable Area */}
        <section className="flex-1 overflow-y-auto p-12 custom-scrollbar">
          <div className="max-w-7xl mx-auto space-y-12 pb-20">
            
            {/* Hero Main Status */}
            <motion.div 
              initial={{ scale: 0.98, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="relative overflow-hidden rounded-[4rem] bg-gradient-to-r from-primary to-secondary p-16 text-text-primary shadow-3xl shadow-primary/20"
            >
              <div className="relative z-10 flex flex-col xl:flex-row xl:items-center justify-between gap-12">
                <div className="space-y-8">
                  <div className="flex items-center gap-8">
                    <div className="bg-white/20 backdrop-blur-xl size-20 rounded-[2rem] flex items-center justify-center border border-white/30 rotate-3 transform">
                      <CheckCircle2 size={48} className="text-green-400" strokeWidth={2.5} />
                    </div>
                    <h2 className="text-6xl font-black tracking-tighter uppercase italic leading-none">All Systems<br/>Operational</h2>
                  </div>
                  <p className="text-xl font-bold text-text-secondary max-w-2xl uppercase tracking-tight leading-relaxed italic">
                    ArogyaAI's infrastructure is currently performing at peak efficiency. All diagnostic pipelines and secure data stores are fully responsive.
                  </p>
                </div>
                <div className="flex flex-col items-center gap-6 shrink-0">
                  <button className="px-12 py-6 bg-white/20 hover:bg-white/30 backdrop-blur-xl border border-white/30 rounded-3xl text-[11px] font-black uppercase tracking-[0.5em] flex items-center gap-4 transition-all hover:scale-105 active:scale-95 italic">
                    <History size={18} className="animate-spin-slow" />
                    Live Metrics
                  </button>
                  <div className="flex flex-col items-center gap-2">
                    <p className="text-[10px] font-black uppercase tracking-[0.4em] text-text-muted italic">Refreshed 12s ago</p>
                    <div className="flex gap-1">
                      {[1,2,3].map(i => <div key={i} className="w-4 h-1 bg-white/30 rounded-full overflow-hidden relative">
                         <motion.div 
                          className="absolute h-full bg-white w-full"
                          animate={{ left: ['-100%', '100%'] }}
                          transition={{ duration: 2, repeat: Infinity, delay: i * 0.3 }}
                         />
                      </div>)}
                    </div>
                  </div>
                </div>
              </div>
              {/* Decorative Elements */}
              <div className="absolute -right-20 -top-20 w-[600px] h-[600px] bg-white/10 rounded-full blur-[160px] animate-pulse"></div>
              <div className="absolute -left-20 -bottom-20 w-[600px] h-[600px] bg-black/10 rounded-full blur-[160px]" style={{ animationDelay: '1s' }}></div>
            </motion.div>

            {/* Quick Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                { label: '90-Day Uptime', value: '99.98%', trend: '+0.02%', color: 'from-green-500 to-emerald-600', sub: 'Calculated global average' },
                { label: 'Avg. API Latency', value: '142ms', trend: 'Stable', color: 'from-primary to-secondary', sub: 'P99 end-to-end response' },
                { label: 'Data Throughput', value: '1.2 TB/s', trend: 'High', color: 'from-secondary to-cyan-500', sub: 'Encrypted HL7 stream volume' }
              ].map((m, i) => (
                <motion.div 
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ delay: 0.1 * i }}
                  key={i} 
                  className="bg-white dark:bg-white/5 p-10 rounded-[3.5rem] border border-slate-100 dark:border-stroke/50 shadow-2xl shadow-primary/5 hover:border-primary/20 transition-all group"
                >
                  <p className="text-[10px] font-black text-text-muted uppercase tracking-[0.2em] mb-4 italic">{m.label}</p>
                  <div className="flex items-end gap-4 mb-8">
                    <span className="text-5xl font-black text-text-primary dark:text-text-primary tracking-tighter italic">{m.value}</span>
                    <span className={`text-[11px] font-black uppercase tracking-widest mb-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-white/5 text-slate-500 group-hover:text-primary transition-colors italic`}>{m.trend}</span>
                  </div>
                  <div className="flex gap-1 h-2.5 mb-6">
                    {[...Array(12)].map((_, j) => (
                      <div key={j} className={`flex-1 rounded-full ${j === 8 ? 'bg-amber-400' : 'bg-green-500'} opacity-${j > 10 ? '20' : '100'} group-hover:animate-pulse`} style={{ animationDelay: `${j * 0.1}s` }}></div>
                    ))}
                  </div>
                  <p className="text-[9px] font-black uppercase tracking-widest text-text-muted opacity-60 italic">{m.sub}</p>
                </motion.div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
              {/* Service Components */}
              <div className="lg:col-span-2 space-y-12">
                <div className="flex items-center justify-between">
                  <h3 className="text-3xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter flex items-center gap-6 italic">
                    <div className="bg-primary size-12 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-primary/20">
                      <Server size={24} strokeWidth={2.5} />
                    </div>
                    Service Components Pulse
                  </h3>
                  <button className="px-6 py-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-stroke rounded-2xl text-[10px] font-black uppercase tracking-widest text-text-primary dark:text-text-primary hover:bg-slate-50 transition-all italic">Refresh All</button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  {services.map((s, idx) => (
                    <motion.div 
                      whileHover={{ scale: 1.02 }}
                      key={idx} 
                      className="bg-white dark:bg-white/5 p-10 rounded-[3rem] border border-slate-100 dark:border-stroke/50 hover:border-primary/20 transition-all group flex items-center justify-between relative overflow-hidden"
                    >
                      <div className="flex items-center gap-8 relative z-10">
                        <div className="size-16 rounded-[1.5rem] bg-primary/5 text-primary flex items-center justify-center group-hover:bg-primary group-hover:text-white transition-all duration-500 shadow-inner group-hover:shadow-primary/30 group-hover:scale-110">
                          {s.icon}
                        </div>
                        <div>
                          <p className="text-base font-black text-text-primary dark:text-text-primary uppercase tracking-widest mb-1 italic leading-none">{s.name}</p>
                          <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest opacity-60 italic">{s.sub}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 bg-green-500/10 text-green-500 px-6 py-2.5 rounded-full text-[10px] font-black uppercase tracking-[0.2em] border border-green-500/10 italic relative z-10">
                        <span className="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse shadow-[0_0_12px_#22c55e]"></span>
                        {s.status}
                      </div>
                      <div className="absolute right-[-10%] bottom-[-10%] size-24 rounded-full bg-primary/5 blur-2xl group-hover:scale-150 transition-transform duration-700"></div>
                    </motion.div>
                  ))}
                </div>

                {/* Vertical Timeline */}
                <div className="space-y-10 pt-10">
                  <div className="flex items-center justify-between">
                    <h3 className="text-3xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter flex items-center gap-6 italic">
                      <div className="bg-primary size-12 rounded-2xl flex items-center justify-center text-white shadow-xl shadow-primary/20">
                        <Clock size={24} strokeWidth={2.5} />
                      </div>
                      Real-time Incident Feed
                    </h3>
                    <button className="text-[11px] font-black text-primary uppercase tracking-[0.2em] hover:bg-primary hover:text-white px-8 py-3 bg-primary/10 rounded-2xl transition-all italic">View Archive</button>
                  </div>
                  <div className="space-y-0 relative before:absolute xl:before:left-12 before:left-8 before:top-10 before:bottom-10 before:w-[3px] before:bg-slate-200 dark:before:bg-white/5 before:rounded-full">
                    {incidents.map((incident, i) => (
                      <motion.div 
                        initial={{ x: -20, opacity: 0 }}
                        whileInView={{ x: 0, opacity: 1 }}
                        viewport={{ once: true }}
                        key={i} 
                        className={`relative xl:pl-32 pl-24 pb-16 ${!incident.active && 'opacity-50 grayscale'}`}
                      >
                        <div className={`absolute xl:left-0 left-[-4px] top-2 size-24 rounded-[2.5rem] bg-white dark:bg-card border-8 ${incident.active ? 'border-primary shadow-2xl shadow-primary/20' : 'border-slate-100 dark:border-stroke/50'} flex items-center justify-center z-10 transform hover:rotate-6 transition-transform duration-500`}>
                          <Check className={`size-10 ${incident.active ? 'text-primary' : 'text-text-primary'} font-black`} strokeWidth={4} />
                        </div>
                        <div className="bg-white dark:bg-white/5 p-12 rounded-[4rem] border border-slate-100 dark:border-stroke/50 shadow-3xl shadow-primary/5 hover:shadow-primary/10 transition-shadow">
                          <div className="flex flex-col md:flex-row md:items-center justify-between gap-8 mb-8">
                            <h4 className="text-2xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter italic">{incident.title}</h4>
                            <span className="px-8 py-3 rounded-full bg-green-500/10 text-green-500 text-[10px] font-black uppercase tracking-[0.2em] border border-green-500/10 italic shrink-0 text-center">{incident.status}</span>
                          </div>
                          <p className="text-lg font-bold text-slate-500 dark:text-text-muted leading-relaxed uppercase tracking-tight italic mb-10">{incident.desc}</p>
                          <div className="flex flex-wrap items-center gap-12 text-[10px] font-black text-text-muted uppercase tracking-[0.3em] italic">
                            <span className="flex items-center gap-3"><Calendar size={18} className="text-primary" /> {incident.date}</span>
                            <span className="flex items-center gap-3"><Clock size={18} className="text-secondary" /> {incident.time}</span>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Sidebar Support / Trust */}
              <div className="space-y-12">
                {/* Maintenance Notice */}
                <div className="bg-white dark:bg-white/5 p-12 rounded-[4rem] border border-slate-100 dark:border-stroke/50 shadow-3xl shadow-primary/5 space-y-10 relative overflow-hidden group">
                  <h3 className="text-2xl font-black text-text-primary dark:text-text-primary uppercase tracking-tighter flex items-center gap-6 italic">
                    <div className="bg-amber-100 dark:bg-amber-500/10 size-12 rounded-2xl flex items-center justify-center text-amber-500 shadow-xl shadow-amber-500/10">
                      <AlertTriangle size={24} strokeWidth={2.5} />
                    </div>
                    System Maintenance
                  </h3>
                  <div className="space-y-8 relative z-10">
                    {[
                      { date: 'Oct 28', title: 'Regional DB Migration', desc: 'Brief intermittent connectivity (approx. 5 mins) during node switchover.', color: 'amber' },
                      { date: 'Nov 02', title: 'Security Patch v4.2', desc: 'Mandatory security update for HIPAA compliance validation layer.', color: 'blue' }
                    ].map((m, i) => (
                      <div key={i} className={`p-8 rounded-[2.5rem] bg-${m.color === 'amber' ? 'amber' : 'blue'}-500/5 border border-${m.color === 'amber' ? 'amber' : 'blue'}-500/10 group/item transition-all hover:bg-${m.color === 'amber' ? 'amber' : 'blue'}-500/10`}>
                        <p className={`text-[10px] font-black text-${m.color === 'amber' ? 'amber' : 'blue'}-500 uppercase tracking-[0.4em] mb-3 italic`}>{m.date}, 2026</p>
                        <p className="text-sm font-black text-text-primary dark:text-text-primary uppercase tracking-tighter mb-3 italic leading-none">{m.title}</p>
                        <p className="text-[11px] font-black text-slate-500 uppercase tracking-tight italic leading-relaxed opacity-80">{m.desc}</p>
                      </div>
                    ))}
                  </div>
                  <div className="absolute left-[-20%] bottom-[-10%] size-40 bg-amber-500/5 rounded-full blur-[60px] group-hover:scale-150 transition-transform duration-1000"></div>
                </div>

                {/* Trust Section */}
                <div className="bg-card p-12 rounded-[4rem] text-text-primary relative overflow-hidden group shadow-3xl shadow-[#13082A]/30">
                  <div className="relative z-10 space-y-8">
                    <div className="space-y-3">
                      <h3 className="text-2xl font-black uppercase tracking-tighter italic">Trust & Security</h3>
                      <p className="text-xs font-bold text-text-primary/50 leading-relaxed uppercase tracking-widest italic leading-tight">Our infrastructure is audited annually for SOC2 Type II, HIPAA, and GDPR compliance.</p>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      {[
                        { icon: <ShieldCheck size={28} className="text-secondary" />, label: 'HIPAA Compliant' },
                        { icon: <Lock size={28} className="text-primary" />, label: 'SOC2 Type II' }
                      ].map((t, i) => (
                        <div key={i} className="p-6 bg-white/5 rounded-3xl flex flex-col items-center gap-4 border border-stroke/50 group-hover:bg-white/10 transition-colors">
                          {t.icon}
                          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-center leading-tight italic">{t.label}</span>
                        </div>
                      ))}
                    </div>
                    <button className="w-full py-6 bg-white text-text-primary font-black text-[11px] uppercase tracking-[0.4em] rounded-[2rem] hover:bg-slate-200 transition-all active:scale-95 italic">
                      Open Security Portal
                    </button>
                  </div>
                  <div className="absolute -right-24 -bottom-24 size-64 bg-primary/20 rounded-full blur-[100px] group-hover:scale-125 transition-transform duration-1000"></div>
                </div>

                {/* Urgent Support */}
                <div className="bg-gradient-to-br from-secondary to-primary p-12 rounded-[4rem] text-text-primary shadow-3xl shadow-primary/20 space-y-10 relative overflow-hidden group">
                  <div className="space-y-4 relative z-10">
                    <h4 className="text-3xl font-black uppercase tracking-tighter italic leading-none">Global<br/>Support</h4>
                    <p className="text-xs font-bold text-text-primary/70 leading-relaxed uppercase tracking-widest italic opacity-80">
                      Our support engineering team is available 24/7 for critical clinical system issues.
                    </p>
                  </div>
                  <div className="space-y-6 relative z-10">
                    <button className="w-full flex items-center gap-6 p-6 bg-white/10 hover:bg-white/20 border border-stroke rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] transition-all italic group/btn">
                      <Mail size={22} className="group-hover:rotate-12 transition-transform" />
                      support@arogyaai.com
                    </button>
                    <button className="w-full flex items-center gap-6 p-6 bg-white/10 hover:bg-white/20 border border-stroke rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] transition-all italic group/btn">
                      <Phone size={22} className="group-hover:rotate-12 transition-transform" />
                      +1 (800) AROGYA-9
                    </button>
                  </div>
                  <div className="absolute -left-10 -top-10 size-48 bg-white/10 rounded-full blur-[60px] group-hover:scale-150 transition-transform duration-1000"></div>
                </div>
              </div>
            </div>
            
            {/* Footer */}
            <footer className="pt-20 border-t border-slate-200 dark:border-stroke/50">
              <div className="flex flex-col md:flex-row justify-between items-center gap-12 opacity-40 hover:opacity-100 transition-opacity">
                <div className="flex items-center gap-4 group">
                  <div className="size-10 rounded-xl bg-slate-300 dark:bg-white/10 flex items-center justify-center group-hover:bg-primary transition-colors">
                    <Activity size={20} className="text-text-primary" strokeWidth={3} />
                  </div>
                  <span className="text-2xl font-black text-slate-500 uppercase tracking-tighter group-hover:text-text-primary dark:group-hover:text-text-primary transition-colors">Arogya<span className="text-text-muted">AI</span></span>
                </div>
                <div className="flex flex-wrap justify-center gap-10">
                  {['Legal', 'Privacy Policy', 'Terms of Service', 'Compliance'].map(link => (
                    <a key={link} href="#" className="text-[10px] font-black text-slate-500 uppercase tracking-[0.3em] hover:text-primary transition-colors italic">{link}</a>
                  ))}
                </div>
                <p className="text-[10px] font-black text-text-muted uppercase tracking-widest italic opacity-60">© 2026 ArogyaAI Systems. Global Monitoring.</p>
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
        
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 8s linear infinite;
        }
      `}} />
    </div>
  );
};

export default SystemStatus;

