import {
  Moon,
  Sun,
  Clock,
  Zap,
  AlertCircle,
  TrendingDown,
  ChevronRight,
  Share2
} from 'lucide-react';
import PageWrapper from '../components/layout/PageWrapper';
import Card from '../components/ui/Card';
import HeroNumber from '../components/ui/HeroNumber';
import ProgressBar from '../components/ui/ProgressBar';
import Tag from '../components/ui/Tag';
import Button from '../components/ui/Button';
import IconBox from '../components/ui/IconBox';
import SleepStackedChart from '../components/charts/SleepStackedChart';
import HeartBreathChart from '../components/charts/HeartBreathChart';
import { wearableData } from '../data/mockData';

const Sleep = () => {
  return (
    <PageWrapper>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Sleep Metric */}
        <Card className="lg:col-span-1 flex flex-col items-center justify-center text-center py-10 gap-4">
          <div className="relative">
            <div className="w-32 h-32 rounded-full border-8 border-primary/10 flex items-center justify-center">
              <div className="flex flex-col items-center">
                <span className="text-3xl font-extrabold font-number text-text-primary">6h 11m</span>
                <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">Total Sleep</span>
              </div>
            </div>
            <div className="absolute top-0 right-0 w-8 h-8 bg-white rounded-full shadow-md flex items-center justify-center">
              <Moon className="text-primary w-4 h-4" />
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-[11px] font-bold text-text-muted uppercase tracking-widest">Sleep Consistency</span>
            <p className="text-sm font-bold text-danger">Dropped 14% from avg</p>
          </div>
        </Card>

        {/* Detailed Breakdown */}
        <Card className="lg:col-span-3 flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-text-primary">Weekly Sleep Stages</h3>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="px-3"><Share2 className="w-3.5 h-3.5" /></Button>
            </div>
          </div>
          <SleepStackedChart data={wearableData.sleep.weekly} height={180} />
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Deep Sleep', val: '45m', color: 'bg-sleep-deep', goal: '1h 30m' },
          { label: 'Light Sleep', val: '4h 12m', color: 'bg-sleep-light', goal: '4h 00m' },
          { label: 'REM Sleep', val: '58m', color: 'bg-success', goal: '1h 45m' },
          { label: 'Awake', val: '14m', color: 'bg-danger', goal: '< 15m' }
        ].map((stage, idx) => (
          <Card key={idx} className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-text-muted uppercase tracking-widest">{stage.label}</span>
              <span className="text-[10px] font-medium text-text-muted">Goal: {stage.goal}</span>
            </div>
            <p className="text-lg font-extrabold text-text-primary font-number">{stage.val}</p>
            <ProgressBar progress={Math.random() * 60 + 20} color={stage.color} height="h-1.5" />
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-text-primary">Heart & Breath Rate (Sleep)</h3>
              <p className="text-[11px] text-text-muted">Stability during overnight recovery</p>
            </div>
            <Tag variant="teal">Vitals Sync</Tag>
          </div>
          <HeartBreathChart data={wearableData.heart_breath} height={200} />
        </Card>

        <Card className="flex flex-col gap-4">
          <h3 className="text-sm font-bold text-text-primary">Sleep Environment Insights</h3>
          <div className="space-y-4">
            <div className="flex items-start gap-4 p-4 bg-background rounded-2xl border border-[#EEEEEE]">
              <IconBox icon={Sun} color="bg-warning" className="w-10 h-10" />
              <div className="flex-1">
                <p className="text-xs font-bold text-text-primary">Early Light Exposure</p>
                <p className="text-[11px] text-text-secondary leading-relaxed mt-1">Detected blue light at 5:45 AM, likely triggering cortisol release and ending REM early.</p>
              </div>
            </div>
            <div className="flex items-start gap-4 p-4 bg-background rounded-2xl border border-[#EEEEEE]">
              <IconBox icon={Zap} color="bg-primary" className="w-10 h-10" />
              <div className="flex-1">
                <p className="text-xs font-bold text-text-primary">Resting Heart Rate Spike</p>
                <p className="text-[11px] text-text-secondary leading-relaxed mt-1">Your RHR was 6 BPM higher than average between 2 AM and 4 AM, indicating poor recovery.</p>
              </div>
            </div>
          </div>
          <Button variant="outline" className="w-full mt-2">See All Insights</Button>
        </Card>
      </div>
    </PageWrapper>
  );
};

export default Sleep;
