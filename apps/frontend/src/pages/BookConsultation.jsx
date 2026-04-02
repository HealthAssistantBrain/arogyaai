import { useState } from 'react';
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
  ChevronDown
} from 'lucide-react';

const BookConsultation = () => {
    const navigate = useNavigate();
    const [selectedSpecialty, setSelectedSpecialty] = useState('All Specialists');
    const [selectedDate, setSelectedDate] = useState('3');
    const [selectedTime, setSelectedTime] = useState('01:00 PM');

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

    const specialties = [
        'All Specialists', 'Cardiology', 'Endocrinology', 'General Practice', 
        'Neurology', 'Oncology', 'Dermatology'
    ];

    const specialists = [
        {
            id: 1,
            name: 'Dr. James Wilson',
            title: 'Senior Neurologist • PhD, Oxford',
            rating: '4.9',
            reviews: '124',
            image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuD3ShAlPUm96P0vzX2oi4w3q4Qe7q9mMor3REJ9Xfvnoaf9T1QMYxDp2wY7GpvoQXUKLYgGk1bXL4_gzhWVureXhNrOu_QiPGOw9dhIe_pSB_e3KpGCHgSa1c81bfBZ5cF2ZAy5ciw9bN_6iNEN4d5n72LH1eUxNQyADDIeXDMU0mmultI716mDPKSas-Oj_Cz4z3PMupWK_Tq1l6wSoAb-KdfxVMzG8lllhnhlhjZ5G8fHCl1E-zpfvVO6WzEtSm8696GenKz_93WE',
            experience: '12 years exp.',
            certification: 'AI Diagnostic Certified',
            availability: 'Available Today',
            status: 'online',
            highlighted: true
        },
        {
            id: 2,
            name: 'Dr. Amara Okafor',
            title: 'Endocrinology Specialist • MD, Yale',
            rating: '5.0',
            reviews: '89',
            image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDFurbCOG3hLD1OGCLhN_rqTHVWmrO0fWPDtbBIGGvASrMJA7UTtx58BoB7Wn-6z1eOAf8mlUf8J7T0q3oReUsgt4x8JPjcr3d5cKqM_QFx6BRqbsO7-VulAV9zNK7kb1m8mRHvhF0acaiRTXgr5DvUKQNWckCXgdVS7_9NYHujqD-jDBbMR4yVWjvH7Z2qLs94-ktI0-TAAlzlizkYkiKIsM1RCFGlYQZUwb0W_4GiQMmrB2XW2kKk8lj-MbrINX5p7R-VSbb7gvbn',
            experience: '8 years exp.',
            certification: 'Metabolic Expert',
            availability: 'Available Today',
            status: 'online'
        },
        {
            id: 3,
            name: 'Dr. Robert Vance',
            title: 'General Practitioner • MD, Stanford',
            rating: '4.7',
            reviews: '210',
            image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBcq_zg0_JMt5V2Mqs61PG5m0nfot_hG-QuINuD71icMcQiAhkufR9as7CrD65t6Hn15gBipaEvAxZncCR0XA_Nz95qG7iLVLpaGDFZCaZnQ0Ol8azIlftPJCIr9gosbuOqiQrgMbJM_f7exCJqDGAIFyGUJO0xtTVKAb7SyMOKMJTJlAQtG0KpZTKKW9z7OCSHLH_Bxr7wz-_9GvrEDbY-brZunRXnEjGGiT2UHFTNG_cgAUh30128Fgif8S4MdKxNpfqpkTu6gRq7',
            experience: '20 years exp.',
            certification: 'Preventative Care',
            availability: 'Next: Monday',
            status: 'offline',
            waitlist: true
        }
    ];

    const calendarDays = [
        { day: '28', currentMonth: false }, { day: '29', currentMonth: false }, { day: '30', currentMonth: false },
        { day: '1', currentMonth: true }, { day: '2', currentMonth: true }, { day: '3', currentMonth: true },
        { day: '4', currentMonth: true }, { day: '5', currentMonth: true }, { day: '6', currentMonth: true },
        { day: '7', currentMonth: true }, { day: '8', currentMonth: true }, { day: '9', currentMonth: true },
        { day: '10', currentMonth: true }, { day: '11', currentMonth: true }
    ];

    const timeSlots = [
        '09:00 AM', '10:30 AM', '01:00 PM', '02:30 PM', '04:00 PM', '05:30 PM'
    ];

    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Sidebar - Standardized Branding */}


                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    {/* Top Navigation Bar - High Fidelity Search */}
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
                            <button className="flex items-center gap-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 px-6 py-3.5 rounded-2xl text-[10px] font-black uppercase tracking-widest text-[#13082a] dark:text-white hover:bg-slate-50 dark:hover:bg-white/10 transition-all shadow-sm active:scale-95 group">
                                <CalendarClock size={18} className="text-slate-400 group-hover:text-[#6143f4]" />
                                My Schedule
                            </button>
                        </div>
                    </header>

                    {/* Scrollable Content */}
                    <div className="flex-1 p-10 custom-scrollbar">
                        <div className="max-w-6xl mx-auto space-y-12 pb-16">
                            
                            {/* Header Section: Title & Video Preview */}
                            <div className="flex flex-col xl:flex-row gap-10 items-start">
                                <div className="flex-1 space-y-6 pt-4">
                                    <h2 className="text-5xl lg:text-6xl font-black tracking-tighter text-[#13082a] dark:text-white leading-[0.9] italic uppercase">Book a<br/>Consultation</h2>
                                    <p className="text-slate-500 font-bold max-w-xl text-base leading-relaxed uppercase tracking-tight text-[15px] opacity-80">Connect with world-class specialists to discuss your AI-driven health insights. Get personalized medical advice based on your digital twin data.</p>
                                </div>
                                
                                {/* Next Session Highlight Card */}
                                <motion.div 
                                    whileHover={{ y: -5 }}
                                    className="w-full xl:w-[420px] shrink-0 bg-[#6143f4] rounded-[2.5rem] p-8 text-white shadow-2xl shadow-[#6143f4]/30 relative overflow-hidden group border border-white/10"
                                >
                                    <div className="relative z-10">
                                        <div className="flex items-center justify-between mb-8">
                                            <div className="flex items-center gap-3">
                                                <div className="size-8 rounded-lg bg-white/10 flex items-center justify-center border border-white/10">
                                                    <Video size={16} strokeWidth={2.5} />
                                                </div>
                                                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-white/90">NEXT SESSION</p>
                                            </div>
                                            <MoreVertical size={18} className="text-white/60 cursor-pointer" />
                                        </div>
                                        <div className="flex items-center gap-6 mb-8">
                                            <div className="size-[72px] rounded-[1.5rem] border-2 border-white/20 p-1 bg-white/5">
                                                <img className="w-full h-full rounded-[1.15rem] object-cover shadow-xl" alt="Dr. Sarah Chen" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCl3-F4lzMLdKRLOmQMwpCT6FNfC7BE_FPX77WLmKuX3f9FsloAeMKzKKkRsE6msHClblsqzCkOflywVxMpRoxBvY8zPYCIK_aD9B7G_ZGsaCPnyKwYfgZ41kVBm4Ojy2KCHkHYVgfwM_PgQYXSnDjCvXseBzGMerg9NvPYAYtEnDjpa6AJoUGUGCjr91jfgpWeMMRVVUm1qQZaafE3hKhz3pqe0unfdBQyGrR7nqtR1A-Z_sVyz9lPSclKXu0HH5T9ZxcxwKhvFW1p"/>
                                            </div>
                                            <div>
                                                <p className="font-black text-2xl tracking-tight leading-none italic uppercase">Dr. Sarah Chen</p>
                                                <p className="text-[11px] font-bold text-white/70 uppercase tracking-widest mt-2">Cardiologist • Senior AI Fellow</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4 text-xs bg-white/10 rounded-[1.5rem] p-4 border border-white/10 backdrop-blur-sm">
                                            <div className="size-10 rounded-xl bg-white/10 flex items-center justify-center shrink-0">
                                                <CalendarClock size={20} />
                                            </div>
                                            <div>
                                                <span className="font-black uppercase tracking-widest block text-[11px]">Tomorrow, 10:00 AM</span>
                                                <span className="text-[9px] font-bold text-white/60 uppercase tracking-widest mt-1 block">Scheduled via Arogya Link</span>
                                            </div>
                                        </div>
                                    </div>
                                    {/* Decorative glow */}
                                    <div className="absolute top-0 right-0 size-64 bg-white/5 rounded-full blur-[100px] pointer-events-none group-hover:bg-white/10 transition-colors"></div>
                                </motion.div>
                            </div>

                            {/* Specialty Filters Matrix */}
                            <div className="space-y-6">
                                <div className="flex items-center justify-between px-2">
                                    <h3 className="font-black text-2xl tracking-tighter text-[#13082a] dark:text-white uppercase italic">Filter by Specialty</h3>
                                    <button className="text-[#6143f4] text-[10px] font-black uppercase tracking-widest hover:underline bg-[#6143f4]/5 px-5 py-2.5 rounded-xl border border-[#6143f4]/10 transition-all active:scale-95">View All Categories</button>
                                </div>
                                <div className="flex gap-4 overflow-x-auto pb-4 no-scrollbar">
                                    {specialties.map(spec => (
                                        <button 
                                            key={spec}
                                            onClick={() => setSelectedSpecialty(spec)}
                                            className={`px-8 py-4 rounded-[1.5rem] font-black text-[11px] uppercase tracking-widest whitespace-nowrap transition-all border-2 ${
                                                selectedSpecialty === spec
                                                ? 'bg-[#6143f4] text-white border-[#6143f4] shadow-2xl shadow-[#6143f4]/30'
                                                : 'bg-white dark:bg-white/5 border-slate-100 dark:border-white/10 text-slate-500 dark:text-slate-400 hover:border-[#6143f4]/30'
                                            }`}
                                        >
                                            {spec}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Main Grid: Doctors & Schedule */}
                            <div className="grid grid-cols-1 xl:grid-cols-12 gap-12 pt-4">
                                {/* Doctor Listing - Left Column (8 units) */}
                                <div className="xl:col-span-7 space-y-8">
                                    <div className="flex items-center justify-between mb-8">
                                        <h3 className="font-black text-2xl tracking-tighter text-[#13082a] dark:text-white uppercase italic flex items-center gap-4">
                                            <div className="size-10 bg-[#6143f4]/10 text-[#6143f4] rounded-xl flex items-center justify-center border border-[#6143f4]/20 shadow-lg shadow-[#6143f4]/5">
                                                <Stethoscope size={22} strokeWidth={2.5} />
                                            </div>
                                            Available Specialists
                                        </h3>
                                        <div className="flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-white/5 rounded-full border border-slate-200 dark:border-white/10">
                                             <span className="size-2 bg-emerald-500 rounded-full animate-pulse"></span>
                                             <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">3 Specialists Online</span>
                                        </div>
                                    </div>
                                    
                                    {specialists.map(doc => (
                                        <motion.div 
                                            key={doc.id} 
                                            whileHover={{ x: 5 }}
                                            className={`bg-white dark:bg-[#131022] rounded-[2.5rem] p-8 lg:p-10 border-2 transition-all group relative overflow-hidden ${
                                                doc.highlighted 
                                                ? 'border-[#6143f4]/20 border-l-[10px] border-l-[#6143f4] shadow-[0_25px_60px_-15px_rgba(97,67,244,0.12)]' 
                                                : 'border-slate-50 dark:border-white/5 shadow-sm'
                                            }`}
                                        >
                                            {doc.waitlist && <div className="absolute inset-0 bg-white/60 dark:bg-[#131022]/80 backdrop-blur-[2px] pointer-events-none z-10 flex items-center justify-center flex-col gap-2">
                                                 <div className="bg-[#13082a] text-white px-5 py-2 rounded-full text-[10px] font-black tracking-widest uppercase">Currently Offline</div>
                                            </div>}
                                            
                                            <div className="flex flex-col md:flex-row gap-10 relative z-20">
                                                <div className="relative shrink-0">
                                                    <div className="size-32 rounded-[2rem] p-1.5 bg-gradient-to-br from-slate-100 to-white dark:from-white/10 dark:to-transparent border border-slate-100 dark:border-white/10">
                                                        <img className={`w-full h-full rounded-[1.65rem] object-cover shadow-inner ${doc.status === 'offline' ? 'grayscale opacity-60' : ''}`} alt={doc.name} src={doc.image}/>
                                                    </div>
                                                    <div className={`absolute -bottom-1 -right-1 size-8 border-4 border-white dark:border-[#131022] rounded-full shadow-lg ${doc.status === 'online' ? 'bg-emerald-500' : 'bg-slate-400'}`}></div>
                                                </div>
                                                <div className="flex-1 flex flex-col justify-between py-1">
                                                    <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6 mb-6">
                                                        <div>
                                                            <h4 className="text-3xl font-black text-[#13082a] dark:text-white tracking-tighter mb-2 italic uppercase group-hover:text-[#6143f4] transition-colors">{doc.name}</h4>
                                                            <p className="text-[11px] font-black text-slate-500 uppercase tracking-widest opacity-80">{doc.title}</p>
                                                        </div>
                                                        <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 px-4 py-2 rounded-2xl text-amber-600 dark:text-amber-400 text-xs font-black shadow-sm shrink-0">
                                                            <Star size={14} className="fill-amber-500" />
                                                            {doc.rating} <span className="opacity-60 text-[10px] font-bold ml-1 uppercase">({doc.reviews} REVIEWS)</span>
                                                        </div>
                                                    </div>
                                                    
                                                    <div className="flex flex-wrap gap-4 mb-8">
                                                        <div className="flex items-center gap-2 bg-slate-50 dark:bg-white/5 px-4 py-2 rounded-xl border border-slate-100 dark:border-white/5 text-[10px] font-black text-slate-500 uppercase tracking-widest">
                                                            <Briefcase size={14} />
                                                            {doc.experience}
                                                        </div>
                                                        <div className="flex items-center gap-2 bg-[#6143f4]/10 text-[#6143f4] px-4 py-2 rounded-xl border border-[#6143f4]/10 text-[10px] font-black uppercase tracking-widest">
                                                            <BadgeCheck size={14} strokeWidth={2.5} />
                                                            {doc.certification}
                                                        </div>
                                                        <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border-2 ${doc.status === 'online' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600' : 'bg-slate-100 dark:bg-white/5 border-slate-200 dark:border-white/10 text-slate-400'} text-[10px] font-black uppercase tracking-widest`}>
                                                            <Zap size={14} />
                                                            {doc.availability}
                                                        </div>
                                                    </div>
                                                    
                                                    <div className="flex gap-4">
                                                        {!doc.waitlist ? (
                                                            <button className="flex-1 bg-[#6143f4] text-white py-4 rounded-[1.25rem] font-black text-[11px] uppercase tracking-[0.2em] hover:bg-[#4a34c1] shadow-[0_15px_30px_-10px_rgba(97,67,244,0.4)] transition-all active:scale-95 leading-none">Book Consultation</button>
                                                        ) : (
                                                            <button className="flex-1 bg-slate-100 dark:bg-white/5 text-slate-400 py-4 rounded-[1.25rem] font-black text-[11px] uppercase tracking-[0.2em] cursor-not-allowed leading-none">Waitlist Full</button>
                                                        )}
                                                        <button className="px-8 bg-white dark:bg-transparent border-2 border-slate-100 dark:border-white/10 text-[#13082a] dark:text-slate-300 rounded-[1.25rem] font-black text-[11px] uppercase tracking-[0.2em] hover:bg-slate-50 dark:hover:bg-white/5 transition-all shadow-sm leading-none">View Profile</button>
                                                    </div>
                                                </div>
                                            </div>
                                            {/* Top-right sparkle for highlighted doctor */}
                                            {doc.highlighted && <div className="absolute top-0 right-0 p-6 opacity-10 pointer-events-none group-hover:opacity-40 transition-opacity">
                                                 <Sparkles size={120} className="text-[#6143f4]" />
                                            </div>}
                                        </motion.div>
                                    ))}
                                </div>

                                {/* Appointment Scheduling - Right Column (5 units) */}
                                <div className="xl:col-span-5 space-y-8">
                                    <h3 className="font-black text-2xl tracking-tighter text-[#13082a] dark:text-white uppercase italic flex items-center gap-4">
                                        <div className="size-10 bg-[#009cde]/10 text-[#009cde] rounded-xl flex items-center justify-center border border-[#009cde]/20 shadow-lg shadow-[#009cde]/5">
                                            <CalendarClock size={22} strokeWidth={2.5} />
                                        </div>
                                        Schedule Selection
                                    </h3>
                                    
                                    <div className="bg-white dark:bg-[#131022] rounded-[3rem] border border-slate-100 dark:border-white/5 p-10 shadow-2xl relative overflow-hidden group/schedule h-fit sticky top-32">
                                         <div className="absolute -top-10 -right-10 p-10 opacity-[0.05] pointer-events-none group-hover/schedule:scale-125 transition-transform duration-1000 rotate-12">
                                            <CalendarClock size={240} className="text-[#6143f4]" />
                                        </div>
                                        
                                        {/* Date Picker Section */}
                                        <div className="mb-10 relative z-10">
                                            <div className="flex items-center justify-between mb-8">
                                                <h4 className="font-black tracking-tight text-xl text-[#13082a] dark:text-white uppercase italic">October 2024</h4>
                                                <div className="flex gap-3">
                                                    <button className="size-11 rounded-2xl border-2 border-slate-100 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/5 flex items-center justify-center transition-all active:scale-90"><ChevronLeft size={20} /></button>
                                                    <button className="size-11 rounded-2xl border-2 border-slate-100 dark:border-white/10 hover:bg-slate-100 dark:hover:bg-white/5 flex items-center justify-center transition-all active:scale-90"><ChevronRight size={20} /></button>
                                                </div>
                                            </div>
                                            
                                            <div className="grid grid-cols-7 gap-1 text-center text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4 border-b border-slate-50 dark:border-white/5 pb-3">
                                                <span>Mo</span><span>Tu</span><span>We</span><span>Th</span><span>Fr</span><span>Sa</span><span>Su</span>
                                            </div>
                                            
                                            <div className="grid grid-cols-7 gap-2 text-center pb-2">
                                                {calendarDays.map((dayObj, index) => (
                                                    <button 
                                                        key={index} 
                                                        disabled={!dayObj.currentMonth}
                                                        onClick={() => setSelectedDate(dayObj.day)}
                                                        className={`h-12 flex items-center justify-center rounded-[1rem] text-xs font-black transition-all border-2 ${
                                                            !dayObj.currentMonth ? 'text-slate-200 dark:text-slate-800 border-transparent cursor-not-allowed' :
                                                            selectedDate === dayObj.day ? 'bg-[#6143f4] text-white border-[#6143f4] shadow-xl shadow-[#6143f4]/30 scale-110 rotate-3' : 
                                                            'hover:bg-[#6143f4]/10 hover:text-[#6143f4] dark:text-slate-400 border-transparent hover:border-[#6143f4]/10'
                                                        }`}
                                                    >
                                                        {dayObj.day}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                        
                                        {/* Time Picker Section */}
                                        <div className="space-y-6 relative z-10">
                                            <div className="flex items-center justify-between">
                                                <p className="text-[11px] font-black uppercase tracking-[0.3em] text-[#13082a] dark:text-white flex items-center gap-3">
                                                    <div className="size-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,1)]"></div>
                                                    Available Slots on Oct {selectedDate}
                                                </p>
                                                <ChevronDown size={14} className="text-slate-400" />
                                            </div>
                                            <div className="grid grid-cols-2 gap-4">
                                                {timeSlots.map(time => (
                                                    <button 
                                                        key={time}
                                                        onClick={() => setSelectedTime(time)}
                                                        className={`py-4 px-4 rounded-[1.25rem] border-2 text-[10px] font-black uppercase tracking-widest transition-all ${
                                                            selectedTime === time 
                                                            ? 'bg-[#6143f4] text-white border-[#6143f4] shadow-xl shadow-[#6143f4]/30' 
                                                            : 'bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/10 text-slate-500 dark:text-slate-400 hover:border-[#6143f4]/30'
                                                        }`}
                                                    >
                                                        {time}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                        
                                        {/* Summary & Payment Section */}
                                        <div className="mt-10 pt-10 border-t border-slate-100 dark:border-white/10 relative z-10">
                                            <div className="flex items-center justify-between mb-8 bg-slate-50 dark:bg-white/5 p-6 rounded-[1.75rem] border-2 border-dashed border-slate-200 dark:border-white/10 shadow-inner group/fee overflow-hidden relative">
                                                <div className="relative z-10">
                                                    <span className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 leading-none block mb-2">CONSULTATION FEE</span>
                                                    <p className="text-[8px] font-bold text-[#6143f4] uppercase tracking-widest leading-none">Standard Specialist Tier</p>
                                                </div>
                                                <span className="font-black text-4xl tracking-tighter text-[#13082a] dark:text-white italic relative z-10">$149<span className="text-sm text-slate-400 font-bold ml-1 opacity-60">.00</span></span>
                                                <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none group-hover/fee:scale-150 transition-transform">
                                                     <Sparkles size={60} />
                                                </div>
                                            </div>
                                            <button className="w-full bg-[#009cde] hover:bg-[#0087c1] text-white py-5 rounded-[1.5rem] font-black text-[11px] uppercase tracking-[0.4em] shadow-2xl shadow-[#009cde]/40 hover:shadow-[#009cde]/60 transition-all active:scale-[0.98] flex items-center justify-center gap-4 cursor-pointer group/pay leading-none">
                                                Proceed to Payment
                                                <ArrowRight size={20} strokeWidth={3} className="group-hover/pay:translate-x-2 transition-transform" />
                                            </button>
                                        </div>
                                    </div>

                                    {/* Trust Badge Section */}
                                    <div className="bg-emerald-50 dark:bg-emerald-500/5 border-2 border-emerald-500/10 p-8 rounded-[2.5rem] flex gap-6 mt-8 shadow-sm group/trust hover:border-emerald-500/20 transition-colors">
                                        <div className="size-16 bg-white dark:bg-white/5 rounded-2xl flex items-center justify-center text-emerald-500 border border-emerald-500/20 shadow-xl shadow-emerald-500/10 shrink-0 group-hover/trust:scale-110 transition-transform">
                                            <ShieldCheck size={32} strokeWidth={1.5} />
                                        </div>
                                        <div>
                                            <h5 className="text-[12px] font-black uppercase tracking-[0.2em] text-emerald-800 dark:text-emerald-400 mb-2 italic">Secure & Confidential</h5>
                                            <p className="text-[11px] font-bold text-emerald-700/80 dark:text-emerald-400/80 leading-relaxed uppercase tracking-tight opacity-90">
                                                All consultations are HIPAA compliant and encrypted end-to-end. Your medical twin data is only shared with the doctor during the active clinical session.
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

export default BookConsultation;
