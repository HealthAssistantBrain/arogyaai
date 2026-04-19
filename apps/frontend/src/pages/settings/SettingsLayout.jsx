import { Outlet } from 'react-router-dom';
import SettingsSidebar from './SettingsSidebar';

const SettingsLayout = () => {
    return (
        <div className="bg-[#f6f5f8] dark:bg-[#0B0819] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col h-screen overflow-hidden antialiased text-[14px]">
            <div className="flex flex-1 overflow-hidden">
                {/* Left Sidebar */}
                <SettingsSidebar />

                {/* Main Content Area */}
                <main className="flex-1 flex flex-col h-full relative overflow-y-auto custom-scrollbar bg-[#f6f5f8] dark:bg-[#0B0819]">
                    <div className="flex-1 p-6 lg:p-10 custom-scrollbar">
                        <Outlet />
                    </div>
                </main>
            </div>

            <style dangerouslySetInnerHTML={{
                __html: `
          .no-scrollbar::-webkit-scrollbar { display: none; }
          .custom-scrollbar::-webkit-scrollbar { width: 5px; height: 5px; }
          .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
          .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.1); border-radius: 20px; }
          .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.3); }
          .leading-none { line-height: 1 !important; }
          .italic { font-style: italic; }
      `}} />
        </div >
    );
};

export default SettingsLayout;
