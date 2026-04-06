import { useEffect } from 'react';
import { Bell, Clock } from 'lucide-react';
import PageWrapper from '../components/layout/PageWrapper';
import Card from '../components/ui/Card';
import IconBox from '../components/ui/IconBox';
import Button from '../components/ui/Button';
import useNotificationStore from '../store/notificationStore';

const Notifications = () => {
  const { notifications, fetchNotifications } = useNotificationStore();

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  return (
    <PageWrapper>
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">Notifications</h2>
        <Button variant="ghost" size="sm" className="text-primary font-bold">Mark all as read</Button>
      </div>
      <div className="space-y-3">
        {notifications.map((n) => (
          <Card key={n.id} className="hover:border-primary/20 cursor-pointer group">
            <div className="flex items-start gap-4">
              <IconBox icon={Bell} color="bg-primary" />
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-text-primary">{n.title}</h4>
                  <span className="text-[10px] text-text-muted flex items-center gap-1">
                    <Clock size={12} />
                    {n.created_at ? new Date(n.created_at).toLocaleString() : ''}
                  </span>
                </div>
                <p className="text-[13px] text-text-secondary mt-1">{n.description}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </PageWrapper>
  );
};

export default Notifications;
