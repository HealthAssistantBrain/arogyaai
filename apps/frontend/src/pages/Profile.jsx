import {
  User,
  MapPin,
  Phone,
  Mail,
  CreditCard,
  ShieldCheck,
  LogOut,
  Edit2,
  ChevronRight,
  Droplets,
  Scale,
  Maximize2
} from 'lucide-react';
import PageWrapper from '../components/layout/PageWrapper';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import IconBox from '../components/ui/IconBox';

const Profile = () => {
  const metrics = [
    { icon: Scale, label: 'Weight', val: '78', unit: 'kg' },
    { icon: Maximize2, label: 'Height', val: '179', unit: 'cm' },
    { icon: Droplets, label: 'Blood Group', val: 'O+', unit: '' },
  ];

  return (
    <PageWrapper>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <Card className="lg:col-span-1 flex flex-col items-center py-10">
          <div className="relative mb-6">
            <div className="w-32 h-32 rounded-full border-4 border-white shadow-lg bg-accent/20 flex items-center justify-center overflow-hidden">
              <User className="w-16 h-16 text-accent" />
            </div>
            <button className="absolute bottom-1 right-1 p-2 bg-primary text-white rounded-full shadow-md hover:scale-110 transition-transform">
              <Edit2 className="w-4 h-4" />
            </button>
          </div>
          <h2 className="text-xl font-extrabold text-text-primary mb-1">Arjun Sharma</h2>
          <p className="text-sm font-medium text-text-secondary flex items-center gap-1 mb-6">
            <MapPin className="w-3.5 h-3.5" /> Mumbai, India
          </p>

          <div className="grid grid-cols-3 gap-8 w-full border-t border-b border-[#F5F5F5] py-6">
            {metrics.map((m, idx) => (
              <div key={idx} className="flex flex-col items-center gap-1">
                <m.icon className="w-4 h-4 text-text-muted mb-1" />
                <span className="text-sm font-bold text-text-primary font-number">{m.val} {m.unit}</span>
                <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">{m.label}</span>
              </div>
            ))}
          </div>

          <div className="w-full mt-6 space-y-2">
            <div className="flex items-center gap-3 p-3 text-text-secondary hover:bg-background rounded-xl transition-colors cursor-pointer group">
              <Mail className="w-4 h-4 group-hover:text-primary" />
              <span className="text-sm font-medium">arjun@example.com</span>
            </div>
            <div className="flex items-center gap-3 p-3 text-text-secondary hover:bg-background rounded-xl transition-colors cursor-pointer group">
              <Phone className="w-4 h-4 group-hover:text-primary" />
              <span className="text-sm font-medium">+91 98765 43210</span>
            </div>
          </div>
        </Card>

        {/* Details & Management */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="flex flex-col gap-6">
            <h3 className="text-sm font-bold text-text-primary">Subscription & Billing</h3>
            <div className="p-5 rounded-2xl bg-primary text-white flex items-center justify-between overflow-hidden relative">
              <div className="absolute right-0 top-0 opacity-10 translate-x-8 translate-y-2">
                <CreditCard size={120} />
              </div>
              <div className="relative z-10 flex flex-col gap-1">
                <span className="text-[10px] font-bold uppercase tracking-widest text-white/60">ArogyaAI Pro</span>
                <p className="text-lg font-bold">Annual Premium Plan</p>
                <p className="text-xs text-white/70">Next billing on Jan 10, 2027</p>
              </div>
              <Button variant="accent" size="sm" className="relative z-10">Manage</Button>
            </div>
          </Card>

          <Card className="flex flex-col gap-2 p-2">
            {[
              { icon: ShieldCheck, label: 'Insurance Data Sync', desc: 'Connected to HDFC Ergo' },
              { icon: CreditCard, label: 'Payment Methods', desc: 'VISA ending in 4242' },
              { icon: LogOut, label: 'Logout', desc: 'Sign out of your account', danger: true },
            ].map((item, idx) => (
              <div key={idx} className={`flex items-center gap-4 p-4 rounded-xl hover:bg-background transition-colors cursor-pointer group ${item.danger ? 'hover:bg-danger/5' : ''}`}>
                <IconBox icon={item.icon} color={item.danger ? 'bg-danger' : 'bg-primary'} className="w-10 h-10" />
                <div className="flex-1">
                  <p className={`text-sm font-bold ${item.danger ? 'text-danger' : 'text-text-primary'}`}>{item.label}</p>
                  <p className="text-[11px] text-text-muted">{item.desc}</p>
                </div>
                <ChevronRight className="w-5 h-5 text-[#DDDDDD] group-hover:text-primary" />
              </div>
            ))}
          </Card>
        </div>
      </div>
    </PageWrapper>
  );
};

export default Profile;
