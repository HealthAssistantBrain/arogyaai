import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, LayoutDashboard, Sparkles, FlaskConical, FileText, Moon, Watch, TrendingUp, History, Upload, Settings, Bell, Wind, Stethoscope } from 'lucide-react';
import { ROUTES } from '../router/routes';

// ── Command registry ─────────────────────────────────────────────────────────
const COMMANDS = [
    { name: 'Dashboard', icon: LayoutDashboard, path: ROUTES.DASHBOARD, keywords: ['home', 'overview'] },
    { name: 'AI Insights', icon: Sparkles, path: ROUTES.INSIGHTS, keywords: ['ai', 'analytics', 'predict'] },
    { name: 'Lab Results', icon: FlaskConical, path: ROUTES.LAB_RESULTS, keywords: ['lab', 'test', 'blood', 'results'] },
    { name: 'Medical Reports', icon: FileText, path: ROUTES.MEDICAL_REPORTS, keywords: ['report', 'pdf', 'document', 'scan'] },
    { name: 'Symptom Analysis', icon: Stethoscope, path: ROUTES.SYMPTOM_ANALYSIS, keywords: ['symptom', 'analysis', 'intake', 'reasoning'] },
    { name: 'Report Generation', icon: FileText, path: ROUTES.REPORT_GENERATION, keywords: ['generated report', 'clinical summary', 'pdf export'] },
    { name: 'Sleep Analysis', icon: Moon, path: ROUTES.SLEEP, keywords: ['sleep', 'rest', 'night'] },
    { name: 'Device Manager', icon: Watch, path: ROUTES.DEVICES, keywords: ['device', 'watch', 'google fit', 'wearable'] },
    { name: 'Disease Simulator', icon: TrendingUp, path: ROUTES.SIMULATOR, keywords: ['simulator', 'risk', 'disease'] },
    { name: 'Health Timeline', icon: History, path: ROUTES.TIMELINE, keywords: ['timeline', 'history', 'log'] },
    { name: 'Upload Report', icon: Upload, path: ROUTES.UPLOAD, keywords: ['upload', 'file', 'import'] },
    { name: 'AQI Monitor', icon: Wind, path: ROUTES.AQI_MONITOR, keywords: ['aqi', 'air', 'environment', 'pollution'] },
    { name: 'Settings', icon: Settings, path: ROUTES.SETTINGS, keywords: ['account', 'profile', 'preferences', 'security'] },
    { name: 'Notifications', icon: Bell, path: ROUTES.NOTIFICATIONS, keywords: ['alerts', 'notification'] },
];

// ── Highlight matching substring ─────────────────────────────────────────────
function Highlight({ text, query }) {
    if (!query.trim()) return <>{text}</>;
    const idx = text.toLowerCase().indexOf(query.toLowerCase());
    if (idx === -1) return <>{text}</>;
    return (
        <>
            {text.slice(0, idx)}
            <mark className="bg-primary/20 text-primary rounded-sm px-0.5 not-italic font-bold">
                {text.slice(idx, idx + query.length)}
            </mark>
            {text.slice(idx + query.length)}
        </>
    );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function CommandPalette() {
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const [query, setQuery] = useState('');
    const [activeIndex, setActiveIndex] = useState(0);
    const inputRef = useRef(null);

    // Filter — match name OR keywords, max 6 results
    const results = query.trim()
        ? COMMANDS.filter(({ name, keywords }) => {
            const q = query.toLowerCase();
            return name.toLowerCase().includes(q) || keywords.some((k) => k.includes(q));
        }).slice(0, 6)
        : COMMANDS.slice(0, 6); // Show first 6 when empty

    // ── Ctrl+K toggle ────────────────────────────────────────────────────────
    useEffect(() => {
        const handler = (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                setOpen((prev) => !prev);
            }
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, []);

    // Focus input when opened
    useEffect(() => {
        if (open) {
            setQuery('');
            setActiveIndex(0);
            setTimeout(() => inputRef.current?.focus(), 0);
        }
    }, [open]);

    // Reset active index when results change
    useEffect(() => { setActiveIndex(0); }, [query]);

    const commit = useCallback((item) => {
        navigate(item.path);
        setOpen(false);
        setQuery('');
    }, [navigate]);

    // ── Keyboard navigation ───────────────────────────────────────────────────
    const handleKeyDown = (e) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            setActiveIndex((i) => Math.min(i + 1, results.length - 1));
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            setActiveIndex((i) => Math.max(i - 1, 0));
        } else if (e.key === 'Enter') {
            if (results[activeIndex]) commit(results[activeIndex]);
        } else if (e.key === 'Escape') {
            setOpen(false);
        }
    };

    if (!open) return null;

    return (
        // Backdrop
        <div
            className="fixed inset-0 z-[9999] bg-black/50 backdrop-blur-sm flex items-start justify-center pt-[10vh]"
            onMouseDown={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
        >
            {/* Panel */}
            <div className="w-full max-w-[560px] mx-4 bg-white dark:bg-background rounded-2xl shadow-2xl border border-slate-200 dark:border-stroke overflow-hidden">

                {/* Search input */}
                <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-100 dark:border-stroke">
                    <Search size={18} className="text-text-muted shrink-0" />
                    <input
                        ref={inputRef}
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Search pages, actions, records..."
                        className="flex-1 bg-transparent text-text-primary dark:text-slate-100 text-sm font-medium placeholder:text-text-muted focus:outline-none"
                        autoComplete="off"
                    />
                    <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded-md bg-slate-100 dark:bg-card text-[10px] font-black text-slate-500 tracking-widest">
                        ESC
                    </kbd>
                </div>

                {/* Results list */}
                <ul role="listbox" className="py-2 max-h-[320px] overflow-y-auto">
                    {results.length > 0 ? results.map((item, idx) => {
                        const Icon = item.icon;
                        const active = idx === activeIndex;
                        return (
                            <li
                                key={item.path}
                                role="option"
                                aria-selected={active}
                                onMouseDown={() => commit(item)}
                                onMouseEnter={() => setActiveIndex(idx)}
                                className={`flex items-center gap-3 px-4 py-2.5 mx-2 rounded-xl cursor-pointer transition-colors ${active
                                    ? 'bg-primary text-white'
                                    : 'text-slate-700 dark:text-text-primary hover:bg-slate-50 dark:hover:bg-card'
                                    }`}
                            >
                                <div className={`flex items-center justify-center size-8 rounded-lg shrink-0 ${active ? 'bg-white/20' : 'bg-slate-100 dark:bg-card'
                                    }`}>
                                    <Icon size={15} className={active ? 'text-text-primary' : 'text-primary'} />
                                </div>
                                <span className="text-sm font-semibold flex-1">
                                    <Highlight text={item.name} query={query} />
                                </span>
                                <span className={`text-[10px] font-black tracking-widest ${active ? 'text-text-primary/50' : 'text-text-muted'
                                    }`}>
                                    {item.path}
                                </span>
                            </li>
                        );
                    }) : (
                        <li className="px-4 py-6 text-center text-sm text-text-muted">
                            No results for{' '}
                            <span className="font-bold text-slate-600 dark:text-text-secondary">"{query}"</span>
                        </li>
                    )}
                </ul>

                {/* Footer hint */}
                <div className="px-4 py-2.5 border-t border-slate-100 dark:border-stroke flex items-center gap-4 text-[10px] font-black text-text-muted uppercase tracking-widest">
                    <span className="flex items-center gap-1"><kbd className="bg-slate-100 dark:bg-card px-1.5 py-0.5 rounded text-text-muted">↑↓</kbd> Navigate</span>
                    <span className="flex items-center gap-1"><kbd className="bg-slate-100 dark:bg-card px-1.5 py-0.5 rounded text-text-muted">↵</kbd> Open</span>
                    <span className="flex items-center gap-1"><kbd className="bg-slate-100 dark:bg-card px-1.5 py-0.5 rounded text-text-muted">Esc</kbd> Close</span>
                </div>
            </div>
        </div>
    );
}

// ── Trigger helper for any component ──────────────────────────────────────────
export const openCommandPalette = () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true, bubbles: true }));
};

// ── Trigger button (use anywhere to open) ─────────────────────────────────────
export function CommandPaletteTrigger({ onClick }) {
    return (
        <button
            onClick={onClick}
            type="button"
            className="flex items-center gap-2.5 px-3 py-2 bg-slate-100 dark:bg-card hover:bg-slate-200 dark:hover:bg-slate-700 rounded-xl text-sm font-medium text-slate-500 dark:text-text-muted transition-colors group"
        >
            <Search size={15} className="group-hover:text-primary transition-colors" />
            <span className="hidden sm:inline text-[13px]">Search...</span>
            <kbd className="hidden sm:inline-flex items-center gap-0.5 ml-1 px-1.5 py-0.5 rounded bg-white dark:bg-background border border-slate-200 dark:border-stroke text-[10px] font-black tracking-wider text-text-muted">
                Ctrl K
            </kbd>
        </button>
    );
}

