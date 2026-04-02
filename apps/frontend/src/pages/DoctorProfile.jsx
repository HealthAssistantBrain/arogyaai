import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/routes';
import { motion } from 'framer-motion';
import { 
  LayoutDashboard, 
  Brain, 
  FlaskConical, 
  History, 
  Activity, 
  FileText, 
  Settings, 
  Bell, 
  ArrowLeft,
  Smartphone,
  User,
  Waves,
  Database,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  Plus,
  Moon,
  HelpCircle,
  Share2,
  Printer,
  Sparkles,
  Search,
  ChevronRight,
  ChevronLeft,
  CalendarClock,
  Clock,
  Stethoscope,
  Star,
  Briefcase,
  BadgeCheck,
  Zap,
  MoreVertical,
  Video,
  Lock,
  ChevronDown,
  MapPin,
  GraduationCap,
  Trophy,
  MessageSquare,
  Heart,
  ChevronUp
} from 'lucide-react';

const DoctorProfile = () => {
    const navigate = useNavigate();

    const sidebarLinks = [
        { icon: LayoutDashboard, label: 'Dashboard', path: ROUTES.DASHBOARD, group: 'Intelligence' },
        { icon: Brain, label: 'AI Insights', path: ROUTES.INSIGHTS, group: 'Intelligence' },
        { icon: FlaskConical, label: 'Disease Simulator', path: ROUTES.SIMULATOR, group: 'Intelligence' },
        { icon: History, label: 'Health Timeline', path: ROUTES.TIMELINE, group: 'History & Labs' },
        { icon: Activity, label: 'Lab Results', path: ROUTES.LAB_RESULTS, group: 'History & Labs' },
        { icon: FileText, label: 'Medical Reports', path: ROUTES.MEDICAL_REPORTS, group: 'History & Labs' },
        { icon: Moon, label: 'Sleep Analysis', path: ROUTES.SLEEP, group: 'History & Labs' },
        { icon: Smartphone, label: 'Device Manager', path: ROUTES.DEVICES, group: 'Management' },
        { icon: User, label: 'Consultation', path: ROUTES.CONSULTATION, group: 'Management', active: true },
        { icon: Settings, label: 'Settings', path: ROUTES.SETTINGS, group: 'Management' },
    ];

    const stats = [
        { value: '15+', label: 'Exp. Years' },
        { value: '2k+', label: 'Consultations' },
        { value: '98%', label: 'Satisfaction' }
    ];

    const specialties = [
        'Predictive Oncology', 'Molecular Genetics', 'CRISPR Diagnostics', 'Rare Genetic Disorders'
    ];

    const credentials = [
        {
            icon: GraduationCap,
            title: 'Johns Hopkins University School of Medicine',
            subtitle: 'MD in Clinical Genetics & PhD in Bioinformatics',
            color: 'primary'
        },
        {
            icon: ShieldCheck,
            title: 'Board Certified in Medical Genetics',
            subtitle: 'American Board of Medical Genetics and Genomics (ABMGG)',
            color: 'secondary'
        },
        {
            icon: Trophy,
            title: 'Global Health Innovator Award 2023',
            subtitle: 'Recognized for excellence in AI-integrated patient care',
            color: 'amber'
        }
    ];

    const testimonials = [
        {
            name: 'Sarah J.',
            image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuChynAmDUgeOqaz90YnR2vtyerlTi9-_sOW0GhC-WIpTc_XARwTscenVH7NRhYq4i-CxG_yQW1igrniFZigpmIHmuD7A2HCAdK30Zx9KGAH0QUFy8zC-Zfcirgncxot9Om8a0cWB3q6GcHrdqjEIc-ASK2kKosrDMDVoIjAZnoGexTIdAE_SLdwAUMiG4E9zNz0hZUSvMuuQH1624fX9-6KlOjiz8rPw4SpKoPSYk0tD53DiEBPX5c6m3BRAxe8456TTeCSbNX6IWGT',
            text: "Dr. Thorne's insights into my family's genetic history were life-changing. He explained everything so clearly.",
            rating: 5
        },
        {
            name: 'Michael R.',
            image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuACUJLEb0l4e3iFjhIRPSkOmCzQm0ut1XF4PG_iTS9K6lCvGKmcz1f6VgqjKVTBmM65EC-7g5w3gTWWIreoDynLp57Zx1UX8C8Wx_V4VMRSUOZDwu07UU1u1CswfWNuZGS1tOqjiAe3gNDjjQ6JhltxJ8WmZPuIATC8ktiUsOfqzD0OC9doIMQoZ2KXr2E2FUlaennNvKv0PnHLl1byAVdIjL1ZOHaRBbSxtapsaHBiJoO0hh6Qxl0p2lJSU0BB036TMtkYasf4a2YM',
            text: "The best genomic specialist I've encountered. The ArogyaAI integration made the whole process seamless.",
            rating: 5
        }
    ];

    const availability = [
        { day: 'Mon, Oct 24', time: '09:30 AM' },
        { day: 'Tue, Oct 25', time: '02:15 PM' },
        { day: 'Wed, Oct 26', time: '11:00 AM' },
        { day: 'Thu, Oct 27', time: '04:45 PM' }
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar */}
                    <header className="h-24 bg-white/80 dark:bg-[#0B0819]/80 backdrop-blur-3xl border-b border-[#6143f4]/10 flex items-center justify-between px-10 shrink-0 sticky top-0 z-20">
                        <div className="flex-1 max-w-xl">
                            <div className="relative group/search">
                                <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within/search:text-[#6143f4] transition-colors" size={18} />
                                <input className="w-full pl-14 pr-6 py-4 bg-slate-100 dark:bg-white/5 border border-transparent rounded-[1.5rem] focus:ring-4 focus:ring-[#6143f4]/10 focus:border-[#6143f4]/30 transition-all text-[13px] text-[#13082a] dark:text-white placeholder:text-slate-400 font-bold uppercase tracking-tight" placeholder="Search for specialists, medical conditions, or reports..." type="text"/>
                            </div>
                        </div>
                        <div className="flex items-center gap-5 ml-8">
                            <button className="size-12 flex items-center justify-center rounded-2xl bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 text-slate-500 hover:bg-[#6143f4]/10 hover:text-[#6143f4] transition-all relative active:scale-95 group shadow-sm">
                                <Bell size={20} />
                                <span className="absolute top-3.5 right-3.5 size-2.5 bg-[#6143f4] rounded-full ring-2 ring-white dark:ring-[#0B0819]"></span>
                            </button>
                            <div className="flex items-center gap-4 ml-2">
                                <div className="text-right hidden sm:block">
                                    <p className="text-xs font-black text-[#13082a] dark:text-white uppercase leading-none">Alex Johnson</p>
                                    <p className="text-[9px] text-[#6143f4] uppercase tracking-widest font-black leading-none mt-1">Premium Member</p>
                                </div>
                                <div className="size-12 rounded-2xl border-2 border-[#6143f4]/20 p-1 bg-white">
                                    <img className="size-full rounded-xl object-cover" alt="Alex Johnson" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDtXYkq58bPS9sE42ldSn-06xk0ePdMg2b2AADGuUBVQEAJ3QcSa0U4ct-KBnUdoXlj2ebPDPo04apV9JoCZ8dSzXGyzNtalj5qC9vUfaWntbUmXdrGKqlUY8sYQVO6kjXPwOGLXTyhDLQXWviw-KKtvC-XPtjlhGOW77UtB__Qng4lIX16DjdLP2HA3uR-2eU3Z2ZaRbeGX_pfA7va16q0A8qRERK7Tib_1ZJAem6YIyzytz9cYnzi5qOY2vojjTG6_6T8ABXgH6ol"/>
                                </div>
                            </div>
                        </div>
                    </header>

                    {/* Scrollable Content */}
                    <div className="flex-1 p-10 custom-scrollbar">
                        <div className="max-w-6xl mx-auto space-y-12 pb-16">
                            
                            {/* Breadcrumbs */}
                            <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                                <button onClick={() => navigate(ROUTES.CONSULTATION)} className="hover:text-[#6143f4] transition-colors leading-none">Consultations</button>
                                <ChevronRight size={14} className="opacity-40" />
                                <span className="text-[#6143f4] leading-none italic">Doctor Profile</span>
                            </div>

                            {/* Profile Header Card - High Fidelity */}
                            <section className="bg-white dark:bg-[#131022] rounded-[3rem] p-10 lg:p-12 shadow-[0_30px_70px_-20px_rgba(97,67,244,0.1)] border border-[#6143f4]/5 relative overflow-hidden group">
                                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-[#6143f4]/5 rounded-full -mr-48 -mt-48 blur-[120px] pointer-events-none group-hover:bg-[#6143f4]/10 transition-colors"></div>
                                <div className="relative z-10 flex flex-col xl:flex-row gap-12 items-start xl:items-center">
                                    <div className="relative shrink-0">
                                        <div className="size-48 md:size-56 rounded-[2.5rem] overflow-hidden border-4 border-white dark:border-white/10 shadow-2xl group-hover:scale-[1.03] transition-transform duration-700 p-1.5 bg-gradient-to-br from-slate-100 to-white dark:from-white/10 dark:to-transparent">
                                            <img className="size-full object-cover rounded-[2rem]" alt="Dr. Aris Thorne" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBmPJQ6qBVRTwAt2NFt4go42uHPfMN7FgDlzMGhlFeQNC5n5tJh8VfD_JrSu5jUZIOI_wK5ZM1X9cA9JeE8jUH37qzaBJ7oAI3uIIEacRSj0asbgyQp0Y6ohRuA3yV7VNP3fX_aULb54rvtcRhR7i7Uf8uDtWcdh9g0FCMjzt1qtkAA7cwpJ6XDgfbslnXlJ1XU3kSICVBPIAylWIZvgbMYflqBQrUpeBHfiV4reWX1o1Cjjz1ibLWJmxQjnndqjv_KlP8eqc5SAZwR"/>
                                        </div>
                                        <div className="absolute -bottom-2 -right-2 bg-emerald-500 text-white size-12 rounded-[1.25rem] flex items-center justify-center border-4 border-white dark:border-[#131022] shadow-xl shadow-emerald-500/30 ring-2 ring-emerald-500/20">
                                            <CheckCircle2 size={24} strokeWidth={3} />
                                        </div>
                                    </div>
                                    <div className="flex-1 space-y-6">
                                        <div className="flex flex-wrap items-center gap-5">
                                            <h1 className="text-5xl lg:text-6xl font-black text-[#13082a] dark:text-white tracking-tighter leading-none italic uppercase">Dr. Aris Thorne</h1>
                                            <div className="px-6 py-2.5 bg-[#009cde]/10 text-[#009cde] text-[10px] font-black rounded-full uppercase tracking-[0.25em] border border-[#009cde]/20 shadow-sm leading-none mt-1">
                                                Verified Specialist
                                            </div>
                                        </div>
                                        <p className="text-2xl text-slate-600 dark:text-slate-400 font-bold max-w-2xl leading-tight uppercase tracking-tight opacity-90">Chief Specialist in Genomic Medicine & <br className="hidden md:block" /> Predictive Oncology</p>
                                        <div className="flex flex-wrap gap-12 items-center pt-4">
                                            <div className="flex items-center gap-4">
                                                <div className="size-11 bg-amber-500/10 text-amber-500 rounded-xl flex items-center justify-center border border-amber-500/20">
                                                    <Star size={22} className="fill-amber-500" />
                                                </div>
                                                <div>
                                                    <span className="text-2xl font-black text-[#13082a] dark:text-white leading-none block italic">4.9</span>
                                                    <span className="text-slate-400 font-bold text-[10px] uppercase tracking-widest leading-none mt-1 block">(1.2k+ reviews)</span>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-4">
                                                <div className="size-11 bg-[#6143f4]/10 text-[#6143f4] rounded-xl flex items-center justify-center border border-[#6143f4]/20">
                                                    <MapPin size={22} />
                                                </div>
                                                <div>
                                                    <span className="text-sm font-black text-[#13082a] dark:text-white leading-none block uppercase">Arogya Central Hospital</span>
                                                    <span className="text-slate-400 font-bold text-[10px] uppercase tracking-widest leading-none mt-1 block">San Francisco, CA</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </section>

                            <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 pt-4">
                                {/* Left Content Column (8 units) */}
                                <div className="lg:col-span-7 space-y-12">
                                    {/* Statistics Grid */}
                                    <div className="grid grid-cols-3 gap-6">
                                        {stats.map((stat) => (
                                            <div key={stat.label} className="bg-white dark:bg-white/5 px-8 py-10 rounded-[2.5rem] text-center border border-slate-100 dark:border-white/10 shadow-sm hover:border-[#6143f4]/30 hover:shadow-xl transition-all group">
                                                <p className="text-[#6143f4] font-black text-4xl tracking-tighter mb-2 italic group-hover:scale-110 transition-transform leading-none">{stat.value}</p>
                                                <p className="text-[10px] uppercase font-black tracking-[0.2em] text-slate-400 opacity-60 leading-none">{stat.label}</p>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Bio & Expertise */}
                                    <section className="bg-white dark:bg-[#131022] p-10 lg:p-12 rounded-[3.5rem] border border-[#6143f4]/5 shadow-sm space-y-10 relative overflow-hidden group/bio">
                                        <div className="absolute top-0 right-0 p-12 opacity-[0.03] dark:opacity-[0.05] pointer-events-none group-hover/bio:scale-125 transition-transform duration-1000 rotate-12">
                                            <Sparkles size={200} className="text-[#6143f4]" />
                                        </div>
                                        <div className="relative z-10">
                                            <h3 className="text-2xl font-black mb-8 flex items-center gap-5 text-[#13082a] dark:text-white uppercase tracking-tight italic">
                                                <div className="size-12 bg-[#6143f4]/10 text-[#6143f4] rounded-[1.25rem] flex items-center justify-center border border-[#6143f4]/20 shadow-lg shadow-[#6143f4]/5">
                                                    <Sparkles size={22} strokeWidth={2.5} />
                                                </div>
                                                Professional Biography
                                            </h3>
                                            <p className="text-slate-600 dark:text-slate-400 leading-relaxed font-bold text-base uppercase tracking-tight opacity-90">
                                                Dr. Aris Thorne is a pioneer in the field of genomic medicine, focusing on the integration of predictive AI models with hereditary cancer screenings. With over 15 years of experience at the intersection of oncology and molecular biology, he has led groundbreaking clinical trials in personalized immunotherapy. 
                                            </p>
                                            <div className="h-4"></div>
                                            <p className="text-slate-500 dark:text-slate-500 leading-relaxed font-bold text-sm uppercase tracking-tight opacity-70">
                                                His approach combines deep data analysis with a patient-centric philosophy, ensuring that each treatment plan is as unique as the patient's own digital twin DNA profile.
                                            </p>
                                            
                                            <div className="mt-12">
                                                <h4 className="font-black mb-6 text-[10px] uppercase tracking-[0.3em] text-slate-400 opacity-60 leading-none">Core Expertise & Digital Proficiency</h4>
                                                <div className="flex flex-wrap gap-4">
                                                    {specialties.map((spec) => (
                                                        <span key={spec} className="px-8 py-4 bg-slate-50 dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-[1.5rem] text-[10px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-300 hover:border-[#6143f4]/40 hover:text-[#6143f4] transition-all cursor-default shadow-sm">
                                                            {spec}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>
                                    </section>

                                    {/* Credentials & Awards */}
                                    <section className="bg-white dark:bg-[#131022] p-10 lg:p-12 rounded-[3.5rem] border border-[#6143f4]/5 shadow-sm space-y-12 relative overflow-hidden group/creds">
                                        <h3 className="text-2xl font-black flex items-center gap-5 text-[#13082a] dark:text-white uppercase tracking-tight italic relative z-10 leading-none">
                                            <div className="size-12 bg-[#009cde]/10 text-[#009cde] rounded-[1.25rem] flex items-center justify-center border border-[#009cde]/20 shadow-lg shadow-[#009cde]/5">
                                                <BadgeCheck size={22} strokeWidth={2.5} />
                                            </div>
                                            Credentials & AI Certification
                                        </h3>
                                        <div className="space-y-10 relative z-10 pt-2">
                                            {credentials.map((cred) => (
                                                <div key={cred.title} className="group flex gap-8 items-start border-l-2 border-slate-100 dark:border-white/5 pl-8 hover:border-[#6143f4]/30 transition-all py-2">
                                                    <div className={`size-16 bg-${cred.color === 'primary' ? '[#6143f4]' : cred.color === 'secondary' ? '[#009cde]' : 'amber-500'}/10 rounded-[1.5rem] flex items-center justify-center text-${cred.color === 'primary' ? '[#6143f4]' : cred.color === 'secondary' ? '[#009cde]' : 'amber-600'} shrink-0 border border-${cred.color === 'primary' ? '[#6143f4]' : cred.color === 'secondary' ? '[#009cde]' : 'amber-500'}/20 group-hover:scale-110 group-hover:shadow-xl transition-all shadow-sm`}>
                                                        <cred.icon size={28} strokeWidth={2.5} />
                                                    </div>
                                                    <div>
                                                        <p className="font-black text-xl text-[#13082a] dark:text-white mb-2 leading-none group-hover:text-[#6143f4] transition-colors italic uppercase tracking-tight">{cred.title}</p>
                                                        <p className="text-sm text-slate-500 font-bold uppercase tracking-tight opacity-70 leading-snug">{cred.subtitle}</p>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </section>

                                    {/* Testimonials */}
                                    <section className="space-y-8">
                                        <div className="flex items-center justify-between px-4">
                                            <h3 className="text-2xl font-black text-[#13082a] dark:text-white uppercase tracking-tight italic leading-none">Patient Clinical Testimonials</h3>
                                            <button className="text-[#6143f4] font-black text-[10px] uppercase tracking-[0.2em] hover:underline bg-[#6143f4]/5 px-6 py-3 rounded-xl border border-[#6143f4]/10 transition-all">View Full Log (1.2k+)</button>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                            {testimonials.map((test) => (
                                                <motion.div 
                                                    key={test.name} 
                                                    whileHover={{ y: -5 }}
                                                    className="bg-white dark:bg-[#131022] p-8 lg:p-10 rounded-[3rem] border border-slate-100 dark:border-white/5 shadow-sm hover:border-[#6143f4]/20 transition-all group/test relative overflow-hidden"
                                                >
                                                    <div className="flex items-center gap-6 mb-8 relative z-10">
                                                        <div className="size-16 rounded-[1.5rem] border-2 border-[#6143f4]/10 p-1 group-hover/test:border-[#6143f4]/30 transition-colors bg-white">
                                                            <img className="size-full rounded-[1.15rem] object-cover shadow-sm" alt={test.name} src={test.image}/>
                                                        </div>
                                                        <div>
                                                            <p className="font-black text-lg text-[#13082a] dark:text-white uppercase leading-none">{test.name}</p>
                                                            <div className="flex text-amber-500 gap-1 mt-2">
                                                                {[...Array(test.rating)].map((_, i) => (
                                                                    <Star key={i} size={14} className="fill-amber-500" />
                                                                ))}
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <p className="text-slate-600 dark:text-slate-400 italic font-bold leading-relaxed text-[13px] uppercase tracking-tight relative z-10 opacity-90">"{test.text}"</p>
                                                    <div className="absolute top-0 right-0 p-6 opacity-[0.05] group-hover/test:scale-150 transition-transform">
                                                        <Activity size={80} className="text-[#6143f4]" />
                                                    </div>
                                                </motion.div>
                                            ))}
                                        </div>
                                    </section>
                                </div>

                                {/* Right Action Column (5 units) */}
                                <div className="lg:col-span-5 space-y-8">
                                    <div className="bg-white dark:bg-[#131022] p-10 lg:p-12 rounded-[3.5rem] border border-[#6143f4]/10 shadow-[0_40px_80px_-20px_rgba(0,156,222,0.15)] sticky top-32 group/action relative overflow-hidden">
                                        <div className="absolute top-0 right-0 p-12 opacity-[0.02] pointer-events-none group-hover/action:rotate-45 transition-transform duration-1000">
                                            <CalendarClock size={250} className="text-[#009cde]" />
                                        </div>
                                        
                                        <div className="mb-12 text-center relative z-10">
                                            <p className="text-slate-400 text-[11px] font-black uppercase tracking-[0.3em] mb-4 opacity-70">Clinical Consultation Fee</p>
                                            <p className="text-6xl font-black text-[#13082a] dark:text-white tracking-tighter italic leading-none">$250<span className="text-lg font-bold text-slate-400 ml-1 opacity-60">/Session</span></p>
                                        </div>
                                        
                                        <div className="space-y-4 relative z-10">
                                            <button onClick={() => navigate(ROUTES.CONSULTATION)} className="w-full bg-[#6143f4] hover:bg-[#4a34c1] text-white font-black py-5 rounded-[1.5rem] shadow-[0_20px_40px_-10px_rgba(97,67,244,0.4)] flex items-center justify-center gap-4 transition-all active:scale-[0.98] hover:scale-[1.02] uppercase text-xs tracking-widest cursor-pointer leading-none">
                                                <CalendarClock size={20} strokeWidth={2.5} />
                                                Book Consultation
                                            </button>
                                            <button className="w-full bg-[#009cde] hover:bg-[#0087c1] text-white font-black py-5 rounded-[1.5rem] shadow-[0_20px_40px_-10px_rgba(0,156,222,0.4)] flex items-center justify-center gap-4 transition-all active:scale-[0.98] hover:scale-[1.02] uppercase text-xs tracking-widest cursor-pointer leading-none">
                                                <MessageSquare size={20} strokeWidth={2.5} />
                                                Message Doctor
                                            </button>
                                            <button className="w-full bg-white dark:bg-transparent border-2 border-slate-100 dark:border-white/10 text-slate-500 hover:text-[#6143f4] hover:border-[#6143f4] font-black py-5 rounded-[1.5rem] flex items-center justify-center gap-4 transition-all uppercase text-xs tracking-widest cursor-pointer leading-none shadow-sm">
                                                <Heart size={20} strokeWidth={2.5} />
                                                Save to Twins
                                            </button>
                                        </div>
                                        
                                        <hr className="my-12 border-slate-100 dark:border-white/5 relative z-10" />
                                        
                                        {/* Availability Mini-Widget */}
                                        <div className="space-y-8 relative z-10">
                                            <div className="flex items-center justify-between">
                                                <h4 className="font-black text-sm uppercase tracking-[0.2em] text-[#13082a] dark:text-white italic">Next Openings</h4>
                                                <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 rounded-lg border border-emerald-500/20 text-emerald-500 text-[9px] font-black uppercase tracking-widest">
                                                    <div className="size-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
                                                    Active Today
                                                </div>
                                            </div>
                                            <div className="grid grid-cols-2 gap-4">
                                                {availability.map((slot) => (
                                                    <div key={slot.day} className="p-5 border-2 border-slate-50 dark:border-white/5 rounded-[1.75rem] text-center hover:bg-[#6143f4]/5 hover:border-[#6143f4]/30 cursor-pointer transition-all bg-slate-50/50 dark:bg-white/5 group/slot relative overflow-hidden">
                                                        <p className="text-[11px] font-black text-[#13082a] dark:text-white mb-2 group-hover/slot:text-[#6143f4] uppercase tracking-tighter leading-none">{slot.day}</p>
                                                        <p className="text-[10px] text-slate-400 font-black uppercase tracking-widest leading-none">{slot.time}</p>
                                                        <div className="absolute top-0 right-0 p-2 opacity-0 group-hover/slot:opacity-100 transition-opacity">
                                                            <Plus size={12} className="text-[#6143f4]" />
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                            <button className="w-full text-center text-[10px] font-black text-slate-400 hover:text-[#6143f4] transition-colors uppercase tracking-[0.3em] bg-slate-50 dark:bg-white/5 py-4 rounded-2xl border border-transparent hover:border-[#6143f4]/10">
                                                View Digital Schedule
                                            </button>
                                        </div>
                                        
                                        {/* Trust Note */}
                                        <div className="mt-12 bg-emerald-50 dark:bg-emerald-500/5 border border-emerald-500/10 p-6 rounded-[2rem] flex gap-4 items-center">
                                            <div className="size-10 bg-white rounded-xl shadow-lg shadow-emerald-500/10 flex items-center justify-center text-emerald-500 shrink-0">
                                                <Lock size={18} strokeWidth={2.5} />
                                            </div>
                                            <p className="text-[10px] font-black text-emerald-800 dark:text-emerald-400 leading-snug uppercase tracking-tight opacity-80">
                                                Arogya-Link ensures 256-bit HIPAA compliance during session transfers.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
            
            <style dangerouslySetInnerHTML={{ __html: `
                .no-scrollbar::-webkit-scrollbar { display: none; }
                .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
                .leading-none { line-height: 1 !important; }
                .italic { font-style: italic; }
            `}} />
        </div>
    );
};

export default DoctorProfile;
