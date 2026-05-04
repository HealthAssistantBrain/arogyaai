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
  Maximize2,
  Calendar,
} from 'lucide-react';
import PageWrapper from '../components/layout/PageWrapper';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import IconBox from '../components/ui/IconBox';
import { useUserStore } from '../store/userStore';
import { calculateAge, calculateBMI } from '../utils/userDerived';

const Profile = () => {
  const { user, loading } = useUserStore();

  if (loading) {
    return (
      <PageWrapper>
        <div className="flex h-64 items-center justify-center text-sm font-semibold text-slate-500">
          Loading profile…
        </div>
      </PageWrapper>
    );
  }

  if (!user) {
    return (
      <PageWrapper>
        <div className="flex h-64 items-center justify-center text-sm font-semibold text-slate-500">
          Profile data unavailable.
        </div>
      </PageWrapper>
    );
  }

  const age = calculateAge(user?.dob);
  const bmi = calculateBMI(user?.height, user?.weight);

  const metrics = [
    { icon: Scale, label: 'Weight', val: user?.weight ? `${user.weight}` : '--', unit: user?.weight ? 'kg' : '' },
    { icon: Maximize2, label: 'Height', val: user?.height ? `${user.height}` : '--', unit: user?.height ? 'cm' : '' },
    { icon: Droplets, label: 'Blood Group', val: user?.blood_group || '--', unit: '' },
  ];

  const displayName = user?.full_name || user?.name || 'User';

  const getInitials = (name) => {
    if (!name) return "--";
    return name
      .trim()
      .split(" ")
      .filter(n => n)
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  };

  const initials = getInitials(user?.full_name || user?.name);

  return (
    <PageWrapper>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <Card className="lg:col-span-1 flex flex-col items-center py-10">
          <div className="relative mb-6">
            <div className="w-32 h-32 rounded-full border-4 border-white shadow-lg bg-accent/20 flex items-center justify-center overflow-hidden">
              {user?.avatar_url ? (
                <img src={user.avatar_url} alt={displayName} className="w-full h-full object-cover" />
              ) : (
                <span className="text-3xl font-black text-accent">{initials}</span>
              )}
            </div>
            <button className="absolute bottom-1 right-1 p-2 bg-primary text-white rounded-full shadow-md hover:scale-110 transition-transform">
              <Edit2 className="w-4 h-4" />
            </button>
          </div>
          <h2 className="text-xl font-extrabold text-text-primary mb-1">{displayName}</h2>
          <p className="text-sm font-medium text-text-secondary flex items-center gap-1 mb-6">
            <MapPin className="w-3.5 h-3.5" /> {user?.city || user?.location || 'Location not set'}
          </p>

          <div className="grid grid-cols-3 gap-8 w-full border-t border-b border-[#F5F5F5] py-6">
            {metrics.map((m, idx) => (
              <div key={idx} className="flex flex-col items-center gap-1">
                <m.icon className="w-4 h-4 text-text-muted mb-1" />
                <span className="text-sm font-bold text-text-primary font-number">{m.val}{m.unit ? ` ${m.unit}` : ''}</span>
                <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">{m.label}</span>
              </div>
            ))}
          </div>

          {/* DOB + Age Row */}
          <div className="w-full mt-5 grid grid-cols-2 gap-4 px-2">
            <div className="flex flex-col items-center gap-1 p-3 rounded-xl bg-slate-50">
              <Calendar className="w-4 h-4 text-text-muted mb-1" />
              <span className="text-sm font-bold text-text-primary">
                {user?.dob ? new Date(user.dob).toLocaleDateString() : '--'}
              </span>
              <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Date of Birth</span>
            </div>
            <div className="flex flex-col items-center gap-1 p-3 rounded-xl bg-slate-50">
              <User className="w-4 h-4 text-text-muted mb-1" />
              <span className="text-sm font-bold text-text-primary">
                {age !== null ? `${age} yrs` : '--'}
              </span>
              <span className="text-[9px] font-bold text-text-muted uppercase tracking-wider">Age</span>
            </div>
          </div>

          {bmi && (
            <p className="mt-4 text-xs font-bold text-primary">BMI: {bmi}</p>
          )}

          <div className="w-full mt-6 space-y-2">
            <div className="flex items-center gap-3 p-3 text-text-secondary hover:bg-background rounded-xl transition-colors cursor-pointer group">
              <Mail className="w-4 h-4 group-hover:text-primary" />
              <span className="text-sm font-medium">{user?.email || 'No email'}</span>
            </div>
            {user?.phone && (
              <div className="flex items-center gap-3 p-3 text-text-secondary hover:bg-background rounded-xl transition-colors cursor-pointer group">
                <Phone className="w-4 h-4 group-hover:text-primary" />
                <span className="text-sm font-medium">{user.phone}</span>
              </div>
            )}
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
                <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted">ArogyaAI Pro</span>
                <p className="text-lg font-bold">Annual Premium Plan</p>
                <p className="text-xs text-text-primary/70">Next billing on Jan 10, 2027</p>
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
              <div
                key={idx}
                className={`flex items-center gap-4 p-4 rounded-xl hover:bg-background transition-colors cursor-pointer group ${item.danger ? 'hover:bg-danger/5' : ''}`}
              >
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

