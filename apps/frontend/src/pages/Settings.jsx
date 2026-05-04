import { Settings as SettingsIcon, User, Bell, Shield, Lock, Globe, HelpCircle } from 'lucide-react';
import PageWrapper from '../components/layout/PageWrapper';
import Card from '../components/ui/Card';
import Toggle from '../components/ui/Toggle';

const Settings = () => {
  return (
    <PageWrapper>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1 space-y-6">
          <nav className="space-y-1">
            {[
              { icon: User, label: 'Account' },
              { icon: Bell, label: 'Notifications' },
              { icon: Shield, label: 'Privacy' },
              { icon: Lock, label: 'Security' },
              { icon: Globe, label: 'Language' },
              { icon: HelpCircle, label: 'Help' },
            ].map((item, idx) => (
              <div key={idx} className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-colors ${idx === 0 ? 'bg-primary text-white shadow-md' : 'text-text-secondary hover:bg-background'}`}>
                <item.icon className="w-4 h-4" />
                <span className="text-sm font-bold">{item.label}</span>
              </div>
            ))}
          </nav>
        </Card>

        <Card className="lg:col-span-2 space-y-8">
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-text-muted">App Settings</h3>
            <Toggle label="Email Notifications" active={true} />
            <Toggle label="Push Notifications" active={true} />
            <Toggle label="Health Reminders" active={false} />
          </div>

          <div className="pt-8 border-t border-[#F5F5F5] space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-text-muted">Regional</h3>
            <div className="flex items-center justify-between p-3 bg-background rounded-xl border border-[#EEEEEE]">
              <span className="text-sm font-bold text-text-primary">Timezone</span>
              <span className="text-xs text-text-secondary font-medium">Asia/Kolkata (GMT+5:30)</span>
            </div>
          </div>
        </Card>
      </div>
    </PageWrapper>
  );
};

export default Settings;

