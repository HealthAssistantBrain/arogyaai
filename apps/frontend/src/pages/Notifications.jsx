import { Bell, Clock, Trash2, CheckCircle } from 'lucide-react';
import PageWrapper from '../components/layout/PageWrapper';
import Card from '../components/ui/Card';
import IconBox from '../components/ui/IconBox';
import Button from '../components/ui/Button';

const Notifications = () => {
  const notifs = [
    { id: 1, title: 'Risk Alert', message: 'Cardiovascular risk elevated. Schedule Lipid Profile.', time: '2h ago', type: 'high_risk' },
    { id: 2, title: 'Device Connected', message: 'Apple Watch successfully synced.', time: '5h ago', type: 'success' },
    { id: 3, title: 'Appointment Reminder', message: 'Consultation with Dr. Sarah tomorrow at 10 AM.', time: '1d ago', type: 'info' },
  ];

  return (
    <PageWrapper>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Notifications</h2>
        <Button variant="ghost" size="sm" className="text-primary font-bold">Mark all as read</Button>
      </div>
      <div className="space-y-3">
        {notifs.map(n => (
          <Card key={n.id} className="hover:border-primary/20 cursor-pointer group">
            <div className="flex items-start gap-4">
              <IconBox icon={Bell} color={n.type === 'high_risk' ? 'bg-danger' : 'bg-primary'} />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-text-primary">{n.title}</h4>
                  <span className="text-[10px] text-text-muted">{n.time}</span>
                </div>
                <p className="text-[13px] text-text-secondary mt-1">{n.message}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </PageWrapper>
  );
};

export default Notifications;
