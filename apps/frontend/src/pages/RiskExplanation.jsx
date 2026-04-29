import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useHealthStore from '../store/healthStore';
import useDashboardStore from '../store/dashboardStore';
import { useAuthStore } from '../store/authStore';
import { ROUTES } from '../router/routes';
import RiskUI from '../components/risk/RiskUI';
import RiskReportSkeleton from '../components/skeleton/RiskReportSkeleton';
import SmartLoadingOverlay from '../components/ui/SmartLoadingOverlay';
import useSmartFetchOverlay from '../hooks/useSmartFetchOverlay';

const RiskExplanation = () => {
    const navigate = useNavigate();
    const authUserId = useAuthStore((state) => state.user?.id ?? null);
    const { fetchHealthMetrics } = useHealthStore();
    const { prediction, fetchDashboardData, isFetching: dashboardIsFetching } = useDashboardStore();
    const dashboardLastFetchedAt = useDashboardStore((state) => state.lastFetchedAt);
    const dashboardCacheOwnerId = useDashboardStore((state) => state.cacheOwnerId);
    const dashboardHydrated = useDashboardStore((state) => state.hasHydratedCache);
    const [riskData, setRiskData] = useState(null);
    const [isPageFetching, setIsPageFetching] = useState(false);

    const hasPredictionSnapshot = dashboardCacheOwnerId === authUserId && Boolean(prediction?.data);
    const currentRiskData = riskData ?? (hasPredictionSnapshot ? prediction?.data : null);
    const explanation = currentRiskData?.explanation ?? null;
    const showSkeleton = !currentRiskData && (isPageFetching || dashboardIsFetching || !dashboardHydrated);
    const showRefreshOverlay = useSmartFetchOverlay(
        isPageFetching || dashboardIsFetching,
        Boolean(currentRiskData) || (dashboardCacheOwnerId === authUserId && dashboardLastFetchedAt !== null),
        { exitDelayMs: 200 }
    );

    useEffect(() => {
        if (!riskData && hasPredictionSnapshot) {
            setRiskData(prediction.data);
        }
    }, [hasPredictionSnapshot, prediction, riskData]);

    useEffect(() => {
        const loadData = async () => {
            setIsPageFetching(true);
            try {
                await Promise.all([
                    fetchHealthMetrics({ silent: true }),
                    fetchDashboardData({ silent: hasPredictionSnapshot })
                ]);
            } catch (error) {
                console.error('Failed to load risk prediction:', error);
                if (prediction?.data) {
                    setRiskData(prediction.data);
                }
            } finally {
                setIsPageFetching(false);
            }
        };

        void loadData();
    }, [fetchHealthMetrics, fetchDashboardData, hasPredictionSnapshot, prediction]);

    if (showSkeleton) {
        return <RiskReportSkeleton />;
    }

    return (
        <div className="relative bg-[#eaeaea] dark:bg-[#131022] text-[#13082a] dark:text-slate-100 min-h-screen font-display flex flex-col overflow-hidden antialiased">
            {showRefreshOverlay ? <SmartLoadingOverlay label="Refreshing risk model" /> : null}
            <main className="flex-1 overflow-y-auto p-8 custom-scrollbar bg-slate-50/30 dark:bg-transparent">
                <RiskUI
                    riskData={currentRiskData}
                    explanation={explanation}
                    loading={!currentRiskData && (isPageFetching || dashboardIsFetching)}
                    onSimulatorClick={() => navigate(ROUTES.SIMULATOR)}
                />
            </main>

            <style dangerouslySetInnerHTML={{
                __html: `
                .custom-scrollbar::-webkit-scrollbar { width: 4px; }
                .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
                .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(97, 67, 244, 0.2); border-radius: 20px; }
                .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(97, 67, 244, 0.4); }
                .font-display { font-family: 'Space Grotesk', sans-serif; }
            `}} />
        </div>
    );
};

export default RiskExplanation;

