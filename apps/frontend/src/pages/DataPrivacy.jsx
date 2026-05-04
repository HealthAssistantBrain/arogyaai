import { ShieldCheck, Eye, EyeOff, ShieldAlert, Lock, Trash2 } from 'lucide-react';
import PageWrapper from '../components/layout/PageWrapper';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Toggle from '../components/ui/Toggle';

const DataPrivacy = () => {
  return (
    <PageWrapper>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 space-y-8">
          <div className="space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-text-muted">Data Sharing</h3>
            <div className="space-y-6">
              <Toggle label="Share data with My Doctors" active={true} />
              <Toggle label="Share data with Insurance Provider" active={false} />
              <Toggle label="Allow research participation (Anonymized)" active={true} />
            </div>
          </div>

          <div className="pt-8 border-t border-[#F5F5F5] space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-text-muted">Data Storage</h3>
            <div className="p-4 bg-background rounded-2xl border border-[#EEEEEE] flex items-center justify-between">
              <div className="flex gap-3">
                <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center text-primary">
                  <Lock size={20} />
                </div>
                <div>
                  <p className="text-sm font-bold">End-to-End Encryption</p>
                  <p className="text-[11px] text-text-muted">Your health records are encrypted at rest.</p>
                </div>
              </div>
              <Tag variant="success">Active</Tag>
            </div>
          </div>
        </Card>

        <Card className="flex flex-col gap-6">
          <h3 className="text-sm font-bold text-text-primary">Download My Data</h3>
          <p className="text-xs text-text-secondary leading-relaxed">
            Request a full export of your personal health data including predictions, simulated outcomes and wearable telemetry.
          </p>
          <Button variant="outline" className="w-full">Request Export (JSON)</Button>

          <div className="pt-6 border-t border-[#F5F5F5] mt-auto">
            <Button variant="danger" className="w-full flex items-center justify-center gap-2">
              <Trash2 className="w-4 h-4" /> Delete My Account
            </Button>
          </div>
        </Card>
      </div>
    </PageWrapper>
  );
};

const Tag = ({ children, variant }) => (
  <span className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-wider ${variant === 'success' ? 'bg-success/10 text-success' : 'bg-gray-100 text-gray-500'}`}>
    {children}
  </span>
);

export default DataPrivacy;

