import { CalendarDays, Sun } from 'lucide-react';
import ChecklistCard from './ChecklistCard';

const ActionTimeline = ({ daily = [], weekly = [] }) => (
  <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-slate-700 dark:text-text-primary">
        <Sun size={18} />
        <h3 className="text-sm font-black uppercase tracking-[0.14em]">Daily checklist</h3>
      </div>
      <ChecklistCard title="Today" items={daily} />
    </div>

    <div className="space-y-3">
      <div className="flex items-center gap-2 text-slate-700 dark:text-text-primary">
        <CalendarDays size={18} />
        <h3 className="text-sm font-black uppercase tracking-[0.14em]">Weekly targets</h3>
      </div>
      <ChecklistCard title="This week" items={weekly} />
    </div>
  </div>
);

export default ActionTimeline;

