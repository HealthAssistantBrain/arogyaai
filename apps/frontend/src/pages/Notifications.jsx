import React, { useEffect } from 'react';
import PageWrapper from '../components/layout/PageWrapper';
import Button from '../components/ui/Button';
import useNotificationStore from '../store/notificationStore';
import NotificationCardV2 from '../components/notifications/NotificationCardV2';
import NotificationSkeleton from '../components/notifications/NotificationSkeleton';

const Notifications = () => {
  const { notifications, fetchNotifications, loading, markAsRead, markAllAsRead } = useNotificationStore();
  const notificationList = Array.isArray(notifications) ? notifications : [];

  useEffect(() => {
    void fetchNotifications().catch(() => { });
  }, [fetchNotifications]);

  return (
    <PageWrapper>
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-xl font-bold">Notifications</h2>
        <Button
          variant="ghost"
          size="sm"
          className="text-primary font-bold"
          onClick={() => markAllAsRead()}
          disabled={loading || notificationList.every(n => n.is_read)}
        >
          Mark all as read
        </Button>
      </div>
      <div className="space-y-4">
        {loading && notificationList.length === 0 ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => <NotificationSkeleton key={i} />)}
          </div>
        ) : notificationList.length > 0 ? (
          notificationList.map((n) => (
            <NotificationCardV2
              key={n.id}
              {...n}
              timestamp={n.created_at}
              onMarkRead={markAsRead}
            />
          ))
        ) : (
          <div className="py-12 text-center text-sm font-medium text-text-secondary">
            No notifications found.
          </div>
        )}
      </div>
    </PageWrapper>
  );
};

export default Notifications;

