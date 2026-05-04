import { Shield, Key, Smartphone, LogIn, Monitor, Trash2 } from 'lucide-react';
import PageWrapper from '../components/layout/PageWrapper';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

const Security = () => {
  const sessions = [
    { device: 'iPhone 15 Pro', location: 'Mumbai, India', date: 'Active Now', current: true },
    { device: 'Chrome on MacOS', location: 'Bengaluru, India', date: 'Mar 05, 10:22 AM', current: false },
    { device: 'iPad Pro', location: 'Mumbai, India', date: 'Mar 01, 11:45 PM', current: false },
  ];

  return (
    <PageWrapper>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="space-y-6">
          <h3 className="text-sm font-bold text-text-primary uppercase tracking-tight">Active Sessions</h3>
          <div className="space-y-3">
            {sessions.map((s, idx) => (
              <div key={idx} className="p-4 bg-background rounded-2xl border border-[#EEEEEE] flex items-center justify-between">
                <div className="flex items-center gap-4">
                  {s.device.includes('iPhone') ? <Smartphone className="text-text-muted" /> : <Monitor className="text-text-muted" />}
                  <div>
                    <p className="text-sm font-bold">{s.device}</p>
                    <p className="text-[11px] text-text-muted">{s.location} • {s.date}</p>
                  </div>
                </div>
                {!s.current && <button className="p-2 text-text-secondary hover:text-danger"><Trash2 size={18} /></button>}
                {s.current && <span className="text-[10px] font-bold text-success uppercase">Current</span>}
              </div>
            ))}
          </div>
          <Button variant="outline" className="w-full text-danger border-danger/20 hover:bg-danger/5">Logout from All Devices</Button>
        </Card>

        <div className="space-y-6">
          <Card className="flex flex-col gap-4">
            <h3 className="text-sm font-bold text-text-primary">Two-Factor Authentication</h3>
            <p className="text-xs text-text-secondary leading-relaxed">
              Add an extra layer of security to your health vault by using 2FA.
            </p>
            <Button>Enable 2FA</Button>
          </Card>

          <Card className="flex flex-col gap-4">
            <h3 className="text-sm font-bold text-text-primary">Change Password</h3>
            <p className="text-xs text-text-secondary leading-relaxed">
              Last changed 4 months ago.
            </p>
            <Button variant="outline">Update Password</Button>
          </Card>
        </div>
      </div>
    </PageWrapper>
  );
};

export default Security;

