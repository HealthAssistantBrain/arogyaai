import { useState, useEffect } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { ClipboardList, ChevronDown, ChevronRight, Settings } from 'lucide-react';
import { navConfig, NavItem } from '../../config/navConfig';
import { ROUTES } from '../../router/routes';

export default function Sidebar() {
    const location = useLocation();
    const navigate = useNavigate();
    const [openSections, setOpenSections] = useState<Record<string, boolean>>({});

    // Auto-expand sections that contain the active route
    useEffect(() => {
        const currentPath = location.pathname;
        const newOpenSections = { ...openSections };
        let changed = false;

        navConfig.forEach(section => {
            section.items.forEach(item => {
                if (item.children) {
                    const isChildActive = item.children.some(child => currentPath.startsWith(child.path));
                    if (isChildActive && !newOpenSections[item.label]) {
                        newOpenSections[item.label] = true;
                        changed = true;
                    }
                }
            });
        });

        if (changed) {
            setOpenSections(newOpenSections);
        }
    }, [location.pathname]);

    const toggleSection = (label: string) => {
        setOpenSections(prev => ({
            ...prev,
            [label]: !prev[label]
        }));
    };

    const renderNavItem = (item: NavItem, depth = 0) => {
        const currentPath = location.pathname;

        // An item is active if its path matches exactly, or if it has children and none are selected but the parent path is matched.
        const isActive = item.children
            ? currentPath === item.path || item.children.some(c => currentPath.startsWith(c.path))
            : currentPath === item.path || (item.path !== '/' && currentPath.startsWith(item.path));

        // For parents without direct navigation, or clicking parent navigates to its root
        const hasChildren = !!item.children && item.children.length > 0;
        const isOpen = openSections[item.label];

        return (
            <div key={item.label} className="w-full">
                <div
                    onClick={() => {
                        if (hasChildren) {
                            toggleSection(item.label);
                            // Also navigate to parent route if it's a valid page
                            if (item.path && item.path !== '#') {
                                navigate(item.path);
                            }
                        } else {
                            navigate(item.path);
                        }
                    }}
                    className={`flex items-center justify-between px-4 py-2.5 rounded-xl cursor-pointer transition-all duration-200 group ${isActive && !hasChildren
                            ? 'bg-[#6143f4] text-white font-bold shadow-lg shadow-[#6143f4]/20'
                            : isActive && hasChildren
                                ? 'bg-[#6143f4]/10 text-[#6143f4] font-bold'
                                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 font-medium'
                        }`}
                    style={{ paddingLeft: `${Math.max(1, depth * 1.5)}rem` }}
                >
                    <div className="flex items-center gap-3">
                        {item.icon && <item.icon size={20} className={isActive && !hasChildren ? 'text-white' : 'text-slate-400 group-hover:text-[#6143f4]'} />}
                        <span className="text-sm tracking-tight">{item.label}</span>
                    </div>
                    {hasChildren && (
                        <div className="text-slate-400">
                            {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        </div>
                    )}
                </div>

                {/* Children */}
                {hasChildren && isOpen && (
                    <div className="mt-1 mb-1 space-y-1 border-l-2 border-slate-100 dark:border-slate-800 ml-6 pl-2">
                        {item.children!.map(child => {
                            const isChildActive = currentPath === child.path || (child.path !== '/' && currentPath.startsWith(child.path));
                            return (
                                <div
                                    key={child.label}
                                    onClick={() => navigate(child.path)}
                                    className={`flex items-center gap-3 px-4 py-2 rounded-lg cursor-pointer transition-all duration-200 ${isChildActive
                                            ? 'bg-[#6143f4] text-white font-bold shadow-md shadow-[#6143f4]/20'
                                            : 'text-slate-500 hover:text-[#6143f4] hover:bg-slate-50 dark:hover:bg-slate-800 font-medium'
                                        }`}
                                >
                                    <span className="text-sm tracking-tight">{child.label}</span>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        );
    };

    return (
        <aside className="w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 flex flex-col h-screen sticky top-0 z-30 shrink-0">
            {/* Logo Header */}
            <div
                className="p-6 flex flex-col gap-2 cursor-pointer border-b border-transparent"
                onClick={() => navigate(ROUTES.DASHBOARD)}
            >
                <div className="flex items-center gap-3">
                    <div className="bg-[#6143f4]/10 p-2 rounded-lg">
                        <ClipboardList size={30} className="text-[#6143f4]" />
                    </div>
                    <div>
                        <h1 className="text-xl font-bold tracking-tight">ArogyaAI</h1>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest leading-none mt-1">Healthcare OS</p>
                    </div>
                </div>
            </div>

            {/* Navigation Sections */}
            <nav className="flex-1 px-4 py-4 space-y-6 overflow-y-auto custom-scrollbar">
                {navConfig.map((section, idx) => (
                    <div key={idx} className="space-y-1">
                        <h3 className="px-4 text-[10px] font-black uppercase tracking-[0.25em] text-slate-400 mb-3 leading-none">
                            {section.section}
                        </h3>
                        <div className="space-y-1">
                            {section.items.map(item => renderNavItem(item))}
                        </div>
                    </div>
                ))}
            </nav>
        </aside>
    );
}
