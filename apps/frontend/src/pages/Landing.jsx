import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  Activity, 
  Sparkles, 
  ArrowRight, 
  PlayCircle, 
  Heart, 
  Monitor, 
  Watch, 
  Brain, 
  Stethoscope,
  Smartphone,
  Dumbbell,
  HeartPulse,
  Star,
  Share2,
  Mail
} from 'lucide-react';
import { ROUTES } from '../router/routes';
import { useAuthStore } from '../store/authStore'; // ← Patch 1

const Landing = () => {
  // ── Patch 1: Conditionally render CTA based on auth state.
  // PAGE ITSELF IS ALWAYS PUBLIC — no auto-redirect applied.
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  return (
    <div className="relative flex min-h-screen w-full flex-col overflow-x-hidden bg-background text-white font-display selection:bg-primary/30">
      
      {/* Top Navigation Bar */}
      <nav className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white">
              <Activity size={24} />
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900">ArogyaAI</span>
          </div>
          <div className="hidden md:flex items-center gap-10">
            <a className="text-sm font-medium text-slate-600 hover:text-primary transition-colors" href="#features">Features</a>
            <a className="text-sm font-medium text-slate-600 hover:text-primary transition-colors" href="#how-it-works">How it Works</a>
            <a className="text-sm font-medium text-slate-600 hover:text-primary transition-colors" href="#integrations">Integrations</a>
            <a className="text-sm font-medium text-slate-600 hover:text-primary transition-colors" href="#testimonials">Testimonials</a>
          </div>
          <div className="flex items-center gap-4">
            {/* ── Patch 1: Swap nav CTA based on auth state */}
            {isAuthenticated ? (
              <Link to={ROUTES.DASHBOARD} className="bg-primary hover:bg-primary/90 text-white px-6 py-2.5 rounded-lg text-sm font-bold shadow-lg shadow-primary/20 transition-all active:scale-95">
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link to={ROUTES.LOGIN} className="hidden sm:block text-sm font-bold text-slate-900 px-4 py-2 hover:bg-slate-100 rounded-lg transition-colors">Log In</Link>
                <Link to={ROUTES.SIGNUP} className="bg-primary hover:bg-primary/90 text-white px-6 py-2.5 rounded-lg text-sm font-bold shadow-lg shadow-primary/20 transition-all active:scale-95">
                  Start Free Analysis
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden pt-20 pb-32 bg-[radial-gradient(circle_at_top_right,rgba(96,67,244,0.15),transparent)]">
          <div className="mx-auto max-w-7xl px-6">
            <div className="flex flex-col lg:flex-row items-center gap-16">
              
              <div className="flex-1 space-y-8 text-center lg:text-left">
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-4 py-1.5 text-primary text-sm font-semibold"
                >
                  <Sparkles size={14} />
                  Next-Gen Health Forecasting
                </motion.div>
                
                <motion.h1 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="text-5xl font-bold leading-[1.1] tracking-tight text-slate-900 md:text-7xl"
                >
                  Master Your Longevity with <span className="text-primary">Predictive Intelligence</span>
                </motion.h1>
                
                <motion.p 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="max-w-xl text-lg text-slate-600 mx-auto lg:mx-0"
                >
                  Unlock AI-driven health insights to stay ahead of potential risks and optimize your daily wellness with the world's most advanced longevity platform.
                </motion.p>
                
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="flex flex-wrap items-center justify-center lg:justify-start gap-4"
                >
                  {/* ── Patch 1: Swap hero CTA based on auth state */}
                  {isAuthenticated ? (
                    <Link to={ROUTES.DASHBOARD} className="bg-primary hover:bg-primary/90 text-white px-8 py-4 rounded-xl text-lg font-bold shadow-xl shadow-primary/20 transition-all flex items-center gap-2 active:scale-95">
                      Go to Dashboard
                      <ArrowRight size={20} />
                    </Link>
                  ) : (
                    <Link to={ROUTES.SIGNUP} className="bg-primary hover:bg-primary/90 text-white px-8 py-4 rounded-xl text-lg font-bold shadow-xl shadow-primary/20 transition-all flex items-center gap-2 active:scale-95">
                      Start Free Analysis
                      <ArrowRight size={20} />
                    </Link>
                  )}
                  <button className="bg-white border border-slate-200 text-slate-900 hover:bg-slate-50 px-8 py-4 rounded-xl text-lg font-bold transition-all flex items-center gap-2 shadow-sm">
                    <PlayCircle size={24} className="text-secondary" />
                    Watch Demo
                  </button>
                </motion.div>
              </div>
              
              <div className="flex-1 relative w-full max-w-[600px]">
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.5 }}
                  className="relative rounded-3xl overflow-hidden shadow-2xl border-8 border-white bg-slate-100"
                >
                  <img 
                    className="w-full h-auto object-cover" 
                    alt="High-tech futuristic medical dashboard showing DNA and health data visualization" 
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuDw4OwA2c22dQOs2-euTB3FcJ0nx4yuPOQeGevR2QXH63zF_lA02OzMuYBNyjXDHggA3LuE0FJwycD_Pi-P_QZEBLD9nCYrNb3BhFIydgFQ2AAvx9niKKZpAd9_ysdaAjmZGDfLlgSEj5_78hBMWJqaPkNRI3uECTUvD8g-0dXO45NP665rfqwiiP1d7XFy43PIRsgmnq02qh9OVQCZ3Qyfub6PAmXa3aHy3qOoHfTBEn2YA7bul1_wBksSUXQ0oQcUpi8GHEDeEQuJ"
                  />
                </motion.div>
                
                {/* Floating Data Card */}
                <motion.div 
                  animate={{ y: [0, -8, 0] }}
                  transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
                  className="absolute -bottom-6 -left-6 bg-white/70 backdrop-blur-md border border-white/30 p-6 rounded-2xl shadow-xl max-w-[240px]"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <Heart size={20} className="text-primary" />
                    <span className="text-sm font-bold">Risk Probability</span>
                  </div>
                  <div className="text-2xl font-bold text-slate-900">8.2% Reduction</div>
                  <div className="mt-2 h-2 w-full bg-slate-200 rounded-full overflow-hidden">
                    <div className="h-full bg-secondary w-3/4"></div>
                  </div>
                </motion.div>
              </div>
            </div>
          </div>
        </section>

        {/* Product Preview Dashboard */}
        <section className="py-24 bg-white">
          <div className="mx-auto max-w-7xl px-6 text-center">
            <h2 className="text-3xl font-bold mb-16">The Future of Personal Healthcare</h2>
            <div className="mx-auto max-w-5xl rounded-2xl bg-background p-4 shadow-inner">
              <motion.div 
                initial={{ opacity: 0, y: 40 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                className="rounded-xl overflow-hidden shadow-2xl border border-slate-200"
              >
                <img 
                  className="w-full h-auto" 
                  alt="Modern clean UI dashboard showing health risk scores and AI insights" 
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuDn-NVWLmaVdNdSHLwye2S_7TzZ2igKPGMQyzA7eYYIOlUn0iLS6i0t5ukNKgdsqM51BTD45eN2O-lDSx010wPoNYgobAoEZcagMP284Tf1SwwZa_QgCFJkyg2Q6vke-QjInR1tCYgMI-8zGabA6WF4nJU9MsIJJlsTZiiNdl1k8FxnmN560iquSIrrzzf_WtWuV4KZUKeEGcOoD3d17O4RNJaBaZ79ORdCbc-T9aH1a5_4h3vJgUPbJnSE8EFDXL7AXy_PNgNklbPV"
                />
              </motion.div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="py-24" id="features">
          <div className="mx-auto max-w-7xl px-6">
            <div className="mb-16 max-w-2xl">
              <h2 className="text-4xl font-bold tracking-tight text-slate-900 mb-4">Advanced Predictive Features</h2>
              <p className="text-slate-600 text-lg">Cutting-edge technology designed for proactive, personalized longevity.</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { 
                  icon: Monitor, 
                  title: 'Predictive Monitoring', 
                  desc: 'Continuous tracking of vital signs to detect anomalies before they become critical issues.',
                  color: 'primary'
                },
                { 
                  icon: Watch, 
                  title: 'Wearable Integration', 
                  desc: 'Seamlessly sync with Apple Health, Google Fit, and Fitbit to centralize all your health data.',
                  color: 'secondary'
                },
                { 
                  icon: Brain, 
                  title: 'AI Risk Analysis', 
                  desc: 'Proprietary deep learning models that calculate long-term health trajectories and risk scores.',
                  color: 'primary'
                },
                { 
                  icon: Stethoscope, 
                  title: 'Medical Insights', 
                  desc: 'Evidence-based clinical suggestions curated by our medical board and verified AI systems.',
                  color: 'secondary' 
                }
              ].map((feature, idx) => (
                <motion.div 
                  key={idx}
                  whileHover={{ y: -5 }}
                  className="bg-white p-8 rounded-xl border border-slate-200 hover:border-primary/30 transition-all hover:shadow-xl group"
                >
                  <div className={`mb-6 inline-flex h-12 w-12 items-center justify-center rounded-lg ${feature.color === 'primary' ? 'bg-primary/10 text-primary group-hover:bg-primary' : 'bg-secondary/10 text-secondary group-hover:bg-secondary'} transition-colors group-hover:text-white`}>
                    <feature.icon size={24} />
                  </div>
                  <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
                  <p className="text-slate-600 text-sm leading-relaxed">{feature.desc}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Integrations Grid */}
        <section className="py-24 bg-background text-text-primary overflow-hidden" id="integrations">
          <div className="mx-auto max-w-7xl px-6">
            <div className="text-center mb-16">
              <h2 className="text-3xl font-bold mb-4">Sync Your Ecosystem</h2>
              <p className="text-text-muted">Connect with the tools you already use to get the full picture.</p>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 opacity-70 grayscale hover:grayscale-0 transition-all duration-500">
              {[
                { name: 'Google Fit', icon: Dumbbell },
                { name: 'Apple Health', icon: Smartphone },
                { name: 'Fitbit', icon: Watch },
                { name: 'Garmin', icon: HeartPulse }
              ].map((item, idx) => (
                <div key={idx} className="flex items-center justify-center p-8 bg-card/50 rounded-2xl border border-stroke hover:bg-card transition-colors group">
                  <item.icon size={36} className="text-text-primary group-hover:text-secondary transition-colors" />
                  <span className="ml-2 font-bold text-xl tracking-tight">{item.name}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* How it Works Section */}
        <section className="py-24" id="how-it-works">
          <div className="mx-auto max-w-7xl px-6">
            <div className="text-center mb-20">
              <h2 className="text-4xl font-bold text-slate-900">Health Intelligence in 3 Steps</h2>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-12 relative">
              <div className="hidden lg:block absolute top-1/2 left-0 w-full h-0.5 bg-slate-200 -translate-y-12"></div>
              {[
                { step: 1, title: 'Connect Data', desc: 'Securely link your wearables and medical history in minutes.' },
                { step: 2, title: 'AI Analysis', desc: 'Our predictive engine identifies biomarkers and potential risk areas.' },
                { step: 3, title: 'Optimization', desc: 'Receive actionable, daily protocols to extend your healthspan.' }
              ].map((item, idx) => (
                <div key={idx} className="relative z-10 flex flex-col items-center text-center">
                  <div className="mb-8 flex h-20 w-20 items-center justify-center rounded-full bg-white shadow-xl text-primary font-bold text-2xl border-4 border-slate-100">
                    {item.step}
                  </div>
                  <h3 className="text-xl font-bold mb-4">{item.title}</h3>
                  <p className="text-slate-600 max-w-xs">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Testimonials Section */}
        <section className="py-24 bg-white/50" id="testimonials">
          <div className="mx-auto max-w-7xl px-6">
            <h2 className="text-3xl font-bold text-center mb-16">Trusted by the Best</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {[
                {
                  name: 'Dr. Marcus Thorne',
                  role: 'Performance Physiologist',
                  text: '"ArogyaAI has redefined how I manage my athletes. The predictive risk scores are terrifyingly accurate and highly actionable."',
                  image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBKWOI7kTCKXYkuCPVdRs0r-rnOPS-2EywS93bJ7ncXPwkRfu0PLfbySZ1N4v_C3bbjTcuuZO9n1AUR4R3Uo9zvkKRnEubqXFYMyQ0DpDzB1Uq_ML0O9dCnmYePywOYk9tY8SxD465M6wKLfgZDNI_BOvIyvnynFg5XUG2Ne22SxGgmVg4aDfcjaNzWoA2ftCc1um2tC8VLl7jtxjav-nRbH7t1mvigjnw1KsWOhHaadvGT-aFyzFf6fWw3_r1-VE6Ldddb70qF9SNT'
                },
                {
                  name: 'Elena Rodriguez',
                  role: 'Ironman Competitor',
                  text: '"I\'ve used every health tech tool out there. This is the first platform that actually gives me insights I can\'t find anywhere else."',
                  image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBqAUfIuljnR9ZsUx6H2zrX7tD2uTa5pGe28_uE_RtFH1mRJOe2saA5x4MVJZd8IsV05l2CNxSHmBajZzMxW2sPEw1QrkqZ6h6kjfMM66cO4hWCSarSxKd3JBwhsg8LiWqv7YnZmaY-ah0eMfC0FCDvbXyzT2Np21zcMhrEkkguABtGAWdvtpwHcqsODJAI-E4nSGp1LWg0CdZ4I6BI2asyEhOBMpRUYmJ3GP7MkgloquMkaLDWE4yHLuC44lHp3kpOWi7sB9Dr23jh'
                },
                {
                  name: 'Dr. Sarah Chen',
                  role: 'Longevity Specialist',
                  text: '"The integration between my clinical data and daily habits has finally bridged the gap in my wellness journey."',
                  image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuB5UBLKxs1-oXWX37xe9gJhQacC9mJwi7UYg24wLXoxoiKIvF2UfvTurDNEKS0y1avtzasTa2ei5BxdWbVWu_8j6zLVHitTgJJ3qUu3AL8Q10jrKVPfVc5YH10QUEIfNE8mmBOb5GseQOSo8L6XnklZw9p2qo7Hd0FM9qjmGzgDKHInygui53t07LWK9-f6y2BwgCDQeHMpZ2pBFNvqxouSpe56_vngXf6-6BWyvOijfvaXV6KBcHHTURKpQJbwhMJDK6snHN-9DEYj'
                }
              ].map((test, idx) => (
                <div key={idx} className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
                  <div>
                    <div className="flex gap-1 text-secondary mb-4">
                      {[...Array(5)].map((_, i) => <Star key={i} size={16} fill="currentColor" />)}
                    </div>
                    <p className="text-slate-700 italic mb-8">{test.text}</p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="h-12 w-12 rounded-full bg-slate-200 overflow-hidden border border-slate-100">
                      <img className="w-full h-full object-cover" alt={test.name} src={test.image} />
                    </div>
                    <div>
                      <div className="font-bold text-slate-900">{test.name}</div>
                      <div className="text-sm text-slate-500">{test.role}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="bg-background text-text-secondary py-16">
          <div className="mx-auto max-w-7xl px-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-16">
              
              <div className="col-span-1 md:col-span-1">
                <div className="flex items-center gap-2 mb-6">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-white">
                    <Activity size={18} />
                  </div>
                  <span className="text-lg font-bold text-text-primary tracking-tight">ArogyaAI</span>
                </div>
                <p className="text-sm leading-relaxed mb-6">
                  Pioneering the future of predictive health intelligence and human longevity.
                </p>
                <div className="flex gap-4">
                  <a className="h-10 w-10 flex items-center justify-center rounded-lg bg-card hover:bg-primary transition-colors" href="#">
                    <Share2 size={16} />
                  </a>
                  <a className="h-10 w-10 flex items-center justify-center rounded-lg bg-card hover:bg-primary transition-colors" href="#">
                    <Mail size={16} />
                  </a>
                </div>
              </div>
              
              <div>
                <h4 className="text-text-primary font-bold mb-6">Product</h4>
                <ul className="space-y-4 text-sm font-medium">
                  <li><Link className="hover:text-text-primary transition-colors" to={ROUTES.DASHBOARD}>Risk Dashboard</Link></li>
                  <li><a className="hover:text-text-primary transition-colors" href="#">AI Analysis</a></li>
                  <li><a class="hover:text-text-primary transition-colors" href="#integrations">Integrations</a></li>
                  <li><a class="hover:text-text-primary transition-colors" href="#">Pricing</a></li>
                </ul>
              </div>
              
              <div>
                <h4 className="text-text-primary font-bold mb-6">Resources</h4>
                <ul className="space-y-4 text-sm font-medium">
                  <li><a className="hover:text-text-primary transition-colors" href="#">Whitepapers</a></li>
                  <li><a className="hover:text-text-primary transition-colors" href="#">Health Blog</a></li>
                  <li><a class="hover:text-text-primary transition-colors" href="#">Security</a></li>
                  <li><a class="hover:text-text-primary transition-colors" href="#">Medical Board</a></li>
                </ul>
              </div>
              
              <div>
                <h4 className="text-text-primary font-bold mb-6">Subscribe</h4>
                <p className="text-sm mb-4">Stay updated with the latest in longevity.</p>
                <div className="flex gap-2">
                  <input className="bg-card border-none rounded-lg px-4 py-2 text-sm w-full focus:ring-1 focus:ring-[var(--color-primary)] text-text-primary" placeholder="Email" type="email" />
                  <button className="bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-lg text-sm font-bold transition-all shrink-0">
                    Join
                  </button>
                </div>
              </div>
              
            </div>
            
            <div className="border-t border-stroke pt-8 flex flex-col md:flex-row justify-between items-center gap-4 text-xs font-medium">
              <p>© 2024 ArogyaAI. All rights reserved.</p>
              <div className="flex gap-8">
                <Link className="hover:text-text-primary" to={ROUTES.PRIVACY}>Privacy Policy</Link>
                <Link className="hover:text-text-primary" to={ROUTES.TERMS}>Terms of Service</Link>
                <a className="hover:text-text-primary" href="#">Cookies</a>
              </div>
            </div>
            
          </div>
        </footer>
      </main>
    </div>
  );
};

export default Landing;

