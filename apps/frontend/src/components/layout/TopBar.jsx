import React from 'react';
import { Bell, Search, Menu } from 'lucide-react';
import { useLocation } from 'react-router-dom';

const TopBar = () => {
    const location = useLocation();

    // Simple breadcrumb logic
    const pathParts = location.pathname.split('/').filter(p => p);
    const pageTitle = pathParts.length > 0
        ? pathParts[pathParts.length - 1].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
        : "Dashboard";

    return (
        <header className="sticky top-0 right-0 h-16 bg-background/80 backdrop-blur-md flex items-center justify-between px-6 z-30 lg:ml-0">
            <div className="flex items-center gap-4">
                <button className="lg:hidden p-2 -ml-2 text-text-secondary">
                    <Menu className="w-5 h-5" />
                </button>
                <h2 className="text-lg font-bold text-text-primary tracking-tight">
                    {pageTitle}
                </h2>
            </div>

            <div className="flex items-center gap-2">
                <button className="p-2 text-text-secondary hover:bg-white hover:shadow-sm rounded-xl transition-all">
                    <Search className="w-5 h-5" />
                </button>
                <button className="p-2 text-text-secondary hover:bg-white hover:shadow-sm rounded-xl transition-all relative">
                    <Bell className="w-5 h-5" />
                    <span className="absolute top-2 right-2 w-2 h-2 bg-danger rounded-full border-2 border-background"></span>
                </button>
            </div>
        </header>
    );
};

export default TopBar;
