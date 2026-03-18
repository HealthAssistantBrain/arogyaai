import React from 'react';
import { NavLink } from 'react-router-dom';
import {
    Home,
    Activity,
    Zap,
    FileText,
    BarChart3,
    Moon,
    FlaskConical,
    Calendar,
    Bell,
    User,
    Settings,
    Cpu,
    ShieldCheck,
    HelpCircle,
    Lightbulb,
    Shield
} from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';

const Sidebar = () => {
    const { user } = useAppStore();

    const navGroups = [
        {
            title: "Main",
            items: [
                { name: "Dashboard", path: "/dashboard", icon: Home },
                { name: "Timeline", path: "/timeline", icon: Activity },
                { name: "Simulate", path: "/simulate", icon: Zap },
                { name: "Reports", path: "/reports", icon: FileText },
                { name: "AI Insights", path: "/ai-insights", icon: Lightbulb },
            ]
        },
        {
            title: "Health",
            items: [
                { name: "Sleep Analysis", path: "/sleep", icon: Moon },
                { name: "Lab Results", path: "/lab-results", icon: FlaskConical },
                { name: "Book Consultation", path: "/book-consultation", icon: Calendar },
            ]
        },
        {
            title: "Settings & System",
            items: [
                { name: "Notifications", path: "/notifications", icon: Bell },
                { name: "Devices", path: "/device-management", icon: Cpu },
                { name: "Data Privacy", path: "/data-privacy", icon: ShieldCheck },
                { name: "Security Audit", path: "/security", icon: Shield },
                { name: "Settings", path: "/settings", icon: Settings },
            ]
        },
        {
            title: "Support",
            items: [
                { name: "Help Center", path: "/help", icon: HelpCircle },
                { name: "What's New", path: "/whats-new", icon: Zap },
                { name: "System Status", path: "/system-status", icon: Activity },
            ]
        }
    ];

    return (
        <aside className="hidden lg:flex flex-col fixed left-0 top-0 h-screen w-[220px] bg-white border-r border-[#EEEEEE] z-40 overflow-y-auto">
            <div className="p-6">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                        <span className="text-white font-bold text-xl leading-none">A</span>
                    </div>
                    <span className="text-xl font-bold tracking-tight text-text-primary">ArogyaAI</span>
                </div>
            </div>

            <nav className="flex-1 px-4 space-y-8 pb-20">
                {navGroups.map((group, idx) => (
                    <div key={idx} className="space-y-1">
                        <h3 className="px-2 text-[10px] font-bold uppercase tracking-wider text-text-muted mb-2">
                            {group.title}
                        </h3>
                        {group.items.map((item) => (
                            <NavLink
                                key={item.path}
                                to={item.path}
                                className={({ isActive }) =>
                                    `flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-200 group ${isActive
                                        ? 'bg-primary text-white shadow-md'
                                        : 'text-text-secondary hover:bg-background hover:text-primary'
                                    }`
                                }
                            >
                                <item.icon className="w-4 h-4" />
                                <span className="text-[13px] font-medium">{item.name}</span>
                            </NavLink>
                        ))}
                    </div>
                ))}
            </nav>

            <div className="p-4 border-t border-[#EEEEEE] bg-white sticky bottom-0">
                <NavLink
                    to="/profile"
                    className="flex items-center gap-3 p-2 rounded-xl hover:bg-background transition-colors"
                >
                    <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center overflow-hidden">
                        {user?.avatar ? (
                            <img src={user.avatar} alt={user.name} className="w-full h-full object-cover" />
                        ) : (
                            <User className="text-accent w-5 h-5" />
                        )}
                    </div>
                    <div className="flex-1 min-w-0">
                        <p className="text-[13px] font-bold text-text-primary truncate">{user?.name || "User"}</p>
                        <p className="text-[11px] text-text-muted truncate">Pro Plan</p>
                    </div>
                </NavLink>
            </div>
        </aside>
    );
};

export default Sidebar;
