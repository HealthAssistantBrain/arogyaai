import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function MainLayout() {
    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] font-display text-[#13082A] dark:text-slate-100 min-h-screen flex antialiased">
            <Sidebar />
            <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto custom-scrollbar">
                <Outlet />
            </div>
        </div>
    );
}
