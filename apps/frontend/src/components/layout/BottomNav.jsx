import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, Activity, Zap, FileText, User } from 'lucide-react';
import { ROUTES } from '../../router/routes';

const BottomNav = () => {
    const tabs = [
        { name: "Home", path: ROUTES.DASHBOARD, icon: Home },
        { name: "Timeline", path: ROUTES.TIMELINE, icon: Activity },
        { name: "Simulate", path: ROUTES.SIMULATOR, icon: Zap },
        { name: "Reports", path: ROUTES.MEDICAL_REPORTS, icon: FileText },
        { name: "Profile", path: ROUTES.SETTINGS_PROFILE, icon: User },
    ];

    return (
        <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-[#EEEEEE] px-6 h-16 flex items-center justify-between z-50">
            {tabs.map((tab) => (
                <NavLink
                    key={tab.path}
                    to={tab.path}
                    className={({ isActive }) =>
                        `flex flex-col items-center justify-center gap-1 transition-colors ${isActive ? 'text-primary' : 'text-text-muted'
                        }`
                    }
                >
                    <tab.icon className="w-5 h-5" />
                    <span className="text-[10px] font-medium">{tab.name}</span>
                </NavLink>
            ))}
        </nav>
    );
};

export default BottomNav;
