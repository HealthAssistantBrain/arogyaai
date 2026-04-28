import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { useSearchParams } from 'react-router-dom';
import {
    Activity, Battery, CheckCircle2, Clock, Link2, RefreshCw, Unplug, User, Watch, ArrowUpRight
} from 'lucide-react';
import toast from 'react-hot-toast';

import {
    disconnectGoogleFit,
    fetchGoogleFitStatus,
    startGoogleFitConnect,
    syncGoogleFit,
} from '../../../lib/googleFitApi';
import { refreshAfterGoogleFitSync } from '../../../lib/googleFitRefresh';
import { setGoogleFitConnectionState } from '../../../lib/googleFitConnectionState';

const DEFAULT_TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

function formatDateTime(value, timezone = DEFAULT_TIMEZONE) {
    if (!value) return 'Not available';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return 'Not available';
    return new Intl.DateTimeFormat('en-US', {
        dateStyle: 'medium',
        timeStyle: 'short',
        timeZone: timezone,
    }).format(parsed);
}

function formatNumber(value) {
    if (value === null || value === undefined || value === '') return '--';
    if (typeof value === 'string' && Number.isNaN(Number(value))) return value;
    const numeric = Number(value);
    return Number.isFinite(numeric) ? new Intl.NumberFormat('en-US').format(numeric) : String(value);
}

function extractErrorMessage(error, fallback) {
    return error?.response?.data?.error || error?.response?.data?.detail || error?.message || fallback;
}

function StatCard({ label, value, helper, icon: Icon }) {
    return (
        <div className="bg-white dark:bg-[#131022] rounded-[2.5rem] p-6 shadow-sm border border-[#6143f4]/5 hover:border-[#6143f4]/20 transition-colors group">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <p className="mb-2 text-[9px] font-black uppercase tracking-[0.2em] text-slate-400 leading-none">{label}</p>
                    <p className="text-2xl font-black tracking-tighter text-[#13082a] dark:text-white uppercase italic leading-none">{value}</p>
                    <p className="mt-2 text-[10px] font-bold uppercase tracking-tight text-slate-500 dark:text-slate-400 opacity-80 leading-none">{helper}</p>
                </div>
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#6143f4]/10 bg-[#6143f4]/5 text-[#6143f4] group-hover:scale-110 transition-transform">
                    <Icon size={18} strokeWidth={2.5} />
                </div>
            </div>
        </div>
    );
}

const SettingsDevices = () => {
    const [searchParams, setSearchParams] = useSearchParams();
    const [status, setStatus] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isConnecting, setIsConnecting] = useState(false);
    const [isSyncing, setIsSyncing] = useState(false);
    const [isDisconnecting, setIsDisconnecting] = useState(false);
    const oauthHandledRef = useRef(false);

    async function loadStatus({ silent = false } = {}) {
        if (!silent) setIsLoading(true);
        try {
            const nextStatus = await fetchGoogleFitStatus();
            setStatus(nextStatus);
            setGoogleFitConnectionState(Boolean(nextStatus?.connected));
        } catch (apiError) {
            setStatus(null);
            setGoogleFitConnectionState(false);
            toast.error(extractErrorMessage(apiError, 'Unable to load Google Fit status right now.'));
        } finally {
            if (!silent) setIsLoading(false);
        }
    }

    useEffect(() => {
        loadStatus();
        // eslint-disable-next-line
    }, []);

    useEffect(() => {
        const googleFitStatus = searchParams.get('googleFit');
        const connectedProvider = searchParams.get('connected');
        const message = searchParams.get('message');
        const isConnectedCallback = googleFitStatus === 'connected' || connectedProvider === 'google_fit';

        if ((!isConnectedCallback && googleFitStatus !== 'error' && !message) || oauthHandledRef.current) {
            return;
        }

        oauthHandledRef.current = true;

        const finalize = async () => {
            if (isConnectedCallback) {
                setGoogleFitConnectionState(true);
                toast.success('Google Fit connected. Starting your first sync.');
                try {
                    await syncGoogleFit({ timezone, days: 30 });
                    await refreshAfterGoogleFitSync();
                } catch (apiError) {
                    toast.error(extractErrorMessage(apiError, 'Google Fit connected, but sync failed.'));
                }
            } else {
                toast.error(message || 'Google Fit connection failed.');
            }

            await loadStatus({ silent: true });
            const nextParams = new URLSearchParams(searchParams);
            nextParams.delete('googleFit');
            nextParams.delete('connected');
            nextParams.delete('message');
            setSearchParams(nextParams, { replace: true });
        };

        void finalize();
        // eslint-disable-next-line
    }, [searchParams, setSearchParams, timezone]);

    const connected = Boolean(status?.connected);
    const timezone = status?.timezone || DEFAULT_TIMEZONE;
    const stats = status?.stats || {};

    const handleConnect = async () => {
        setIsConnecting(true);
        try {
            const response = await startGoogleFitConnect({
                timezone,
                redirectPath: window.location.pathname,
            });
            if (response?.auth_url) {
                window.location.assign(response.auth_url);
                return;
            }
            throw new Error('Google Fit did not return an authorization URL.');
        } catch (apiError) {
            toast.error(extractErrorMessage(apiError, 'Unable to start connection.'));
            setIsConnecting(false);
        }
    };

    const handleSync = async () => {
        setIsSyncing(true);
        try {
            const response = await syncGoogleFit({ timezone, days: 30 });
            await Promise.all([
                loadStatus({ silent: true }),
                refreshAfterGoogleFitSync(),
            ]);
            toast.success(response?.message || 'Google Fit sync completed.');
        } catch (apiError) {
            toast.error(extractErrorMessage(apiError, 'Google Fit sync failed.'));
        } finally {
            setIsSyncing(false);
        }
    };

    const handleDisconnect = async () => {
        setIsDisconnecting(true);
        try {
            await disconnectGoogleFit();
            await loadStatus({ silent: true });
            setGoogleFitConnectionState(false);
            toast.success('Google Fit disconnected.');
        } catch (apiError) {
            toast.error(extractErrorMessage(apiError, 'Unable to disconnect Google Fit.'));
        } finally {
            setIsDisconnecting(false);
        }
    };

    return (
        <div className="max-w-6xl mx-auto space-y-12 pb-16">
            {/* Page Header */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 pb-4 border-b border-[#6143f4]/5">
                <div className="space-y-4">
                    <h2 className="text-5xl font-black text-[#13082a] dark:text-white tracking-tighter uppercase italic leading-none">Connected Devices</h2>
                    <p className="text-lg text-slate-500 dark:text-slate-400 font-bold uppercase tracking-tight opacity-80 leading-none max-w-2xl">Manage wearables, sync fitness data, and control hardware endpoints.</p>
                </div>
            </div>

            <div className="space-y-12">
                {/* Google Fit Card */}
                <div className="bg-white dark:bg-[#131022] rounded-[3.5rem] shadow-[0_40px_80px_-20px_rgba(97,67,244,0.05)] border border-[#6143f4]/5 overflow-hidden transition-all duration-500 hover:border-[#6143f4]/20 group/card relative">
                    <div className="px-10 py-10 border-b border-slate-100 dark:border-white/5 flex flex-col md:flex-row justify-between items-start md:items-center gap-6 bg-slate-50/30 dark:bg-transparent relative z-10">
                        <div className="flex items-center gap-5">
                            <div className="size-16 bg-[#6143f4]/10 rounded-[1.5rem] flex items-center justify-center text-[#6143f4] group-hover/card:scale-110 transition-transform shadow-inner shrink-0 lg:shrink">
                                <Activity size={32} strokeWidth={2.5} />
                            </div>
                            <div>
                                <h3 className="text-3xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none mb-2">Google Fit Pipeline</h3>
                                <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight leading-none">Synchronize physical telemetry directly from Android and WearOS endpoints.</p>
                            </div>
                        </div>
                        <div className={`flex items-center gap-3 px-6 py-2.5 rounded-full font-black text-[10px] uppercase tracking-widest shadow-sm leading-none shrink-0 ${isLoading ? 'bg-slate-200/50 text-slate-500 dark:bg-white/10 dark:text-slate-300' : connected ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'}`}>
                            <div className={`size-1.5 rounded-full ${isLoading ? 'bg-slate-400' : connected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`}></div>
                            <span>{isLoading ? 'INITIATING...' : connected ? 'CONNECTED & ACTIVE' : 'NATIVE PIPELINE DISCONNECTED'}</span>
                        </div>
                    </div>

                    <div className="p-10 lg:p-14 relative z-10">
                        {isLoading ? (
                            <div className="flex items-center gap-4 py-8">
                                <div className="size-5 border-4 border-[#6143f4]/20 border-t-[#6143f4] rounded-full animate-spin"></div>
                                <span className="text-xs font-black text-slate-400 uppercase tracking-widest">Querying Google Hardware Sensors...</span>
                            </div>
                        ) : connected ? (
                            <div className="space-y-12">
                                {/* Connection Overview */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 bg-slate-50 dark:bg-[#0B0819]/50 rounded-[2.5rem] p-8 border border-[#6143f4]/5">
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-widest text-[#6143f4]">
                                            <User size={14} /> Linked Identity Account
                                        </div>
                                        <p className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-tight">{status?.google_email || 'Hidden Google Account'}</p>
                                    </div>
                                    <div className="space-y-4">
                                        <div className="flex items-center gap-3 text-[10px] font-black uppercase tracking-widest text-[#6143f4]">
                                            <Clock size={14} /> Last Synchronization Epoch
                                        </div>
                                        <p className="text-sm font-black text-[#13082a] dark:text-white uppercase tracking-tight">{formatDateTime(status?.last_synced_at, timezone)}</p>
                                    </div>
                                </div>

                                {/* Control Actions */}
                                <div className="flex flex-col sm:flex-row items-center gap-4 border-b border-slate-100 dark:border-white/5 pb-12">
                                    <button
                                        onClick={handleSync}
                                        disabled={isSyncing}
                                        className="w-full sm:w-auto bg-[#6143f4]/10 hover:bg-[#6143f4]/20 border border-[#6143f4]/20 text-[#6143f4] px-10 py-5 rounded-[1.5rem] font-black text-[10px] uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3 active:scale-95 leading-none disabled:opacity-50"
                                    >
                                        <RefreshCw size={16} className={isSyncing ? 'animate-spin' : ''} strokeWidth={3} />
                                        {isSyncing ? 'SYNCHRONIZING...' : 'SYNC PREVIOUS 30 DAYS'}
                                    </button>
                                    <button
                                        onClick={handleDisconnect}
                                        disabled={isDisconnecting}
                                        className="w-full sm:w-auto bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-500 px-10 py-5 rounded-[1.5rem] font-black text-[10px] uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3 active:scale-95 leading-none disabled:opacity-50"
                                    >
                                        <Unplug size={16} strokeWidth={3} />
                                        {isDisconnecting ? 'DISCONNECTING...' : 'SEVER CONNECTION'}
                                    </button>
                                </div>

                                {/* Stats Grid */}
                                <div>
                                    <div className="flex items-center gap-4 mb-6">
                                        <div className="size-1.5 bg-[#6143f4] rounded-full"></div>
                                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">Telemetry Aggregation</h4>
                                    </div>
                                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                                        <StatCard label="Daily Locomotion" value={formatNumber(stats.latest_day?.steps)} helper={stats.latest_day?.date ? `Epoch: ${stats.latest_day.date}` : 'Awaiting sensor data'} icon={Watch} />
                                        <StatCard label="Total Trajectory" value={formatNumber(stats.total_steps)} helper="Aggregated matrix span" icon={RefreshCw} />
                                        <StatCard label="Mean Velocity" value={formatNumber(stats.average_daily_steps)} helper="Daily mean across buckets" icon={Clock} />
                                        <StatCard label="Active Epochs" value={formatNumber(stats.active_day_count)} helper="Records containing motion" icon={Battery} />
                                        <StatCard label="Peak Velocity" value={formatNumber(stats.best_day?.steps)} helper={stats.best_day?.date ? `Epoch: ${stats.best_day.date}` : 'No baseline registered'} icon={CheckCircle2} />
                                        <StatCard label="Temporal Zone" value={timezone} helper="Synchronization meridian" icon={ArrowUpRight} />
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="py-8">
                                <div className="bg-slate-50 dark:bg-[#0B0819]/50 rounded-[3rem] p-12 lg:p-16 border border-slate-100 dark:border-white/5 text-center flex flex-col items-center justify-center relative overflow-hidden">

                                    <div className="size-24 bg-white dark:bg-[#131022] rounded-[2.5rem] flex items-center justify-center shadow-2xl mb-8 relative z-10 border border-[#6143f4]/10">
                                        <Activity size={40} className="text-[#6143f4]" />
                                    </div>
                                    <h4 className="text-3xl font-black text-[#13082a] dark:text-white uppercase tracking-tighter italic leading-none mb-4 relative z-10">Sensor Link Required</h4>
                                    <p className="text-sm font-bold text-slate-500 dark:text-slate-400 max-w-lg mx-auto uppercase tracking-tight opacity-80 leading-relaxed mb-10 relative z-10">
                                        Establish a secure OAuth tunnel to import your wearable biometric data directly into the ArogyaAI forecasting engine.
                                    </p>

                                    <button
                                        onClick={handleConnect}
                                        disabled={isConnecting}
                                        className="bg-[#6143f4] text-white px-12 py-6 rounded-[1.5rem] font-black text-xs uppercase tracking-[0.25em] hover:bg-[#4a34c1] hover:scale-105 active:scale-95 transition-all shadow-[0_20px_40px_-10px_rgba(97,67,244,0.4)] flex items-center justify-center gap-4 leading-none disabled:opacity-50 relative z-10"
                                    >
                                        <Link2 size={18} strokeWidth={3} />
                                        {isConnecting ? 'ESTABLISHING HANDSHAKE...' : 'AUTHORIZE GOOGLE FIT'}
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Implementation Info Card */}
                <div className="bg-white/50 dark:bg-[#131022]/50 backdrop-blur-xl rounded-[2.5rem] p-8 border border-slate-100 dark:border-white/5">
                    <div className="flex items-center gap-4 mb-4">
                        <div className="size-1.5 bg-[#009cde] rounded-full"></div>
                        <h4 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.3em] leading-none">System Integrations Note</h4>
                    </div>
                    <ul className="space-y-4 text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tight opacity-80 list-none">
                        <li className="flex items-start gap-3"><span className="text-[#009cde] mt-0.5">•</span> Uses live backend status evaluation on mount.</li>
                        <li className="flex items-start gap-3"><span className="text-[#009cde] mt-0.5">•</span> Smart conditional polling only operates while "CONNECTED & ACTIVE".</li>
                        <li className="flex items-start gap-3"><span className="text-[#009cde] mt-0.5">•</span> Direct data synchronization avoids client-side bottlenecks.</li>
                    </ul>
                </div>
            </div>
        </div>
    );
};

export default SettingsDevices;
