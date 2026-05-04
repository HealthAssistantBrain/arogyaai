import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ReferenceArea
} from 'recharts';
import { safeArray } from '../../utils/safeData';

const NORMAL_MIN = 60;
const NORMAL_MAX = 100;
const CHART_MIN = 0;
const CHART_MAX = 200;
const HOUR_TICKS = Array.from({ length: 24 }, (_, hour) => hour);
const formatHourLabel = (hour) => `${String(hour).padStart(2, '0')}:00`;

const getHeartRateStatus = (payload = {}) => {
    const value = Number(payload.value);

    if (!Number.isFinite(value)) return 'No reading';
    if (payload.is_anomaly) return 'Anomaly';
    if (value < NORMAL_MIN) return 'Low';
    if (value > NORMAL_MAX) return 'Elevated';
    return 'Normal';
};

const renderAnomalyDot = ({ cx, cy, payload }) => {
    const value = Number(payload?.value);
    const isAnomaly = Boolean(payload?.is_anomaly) || (Number.isFinite(value) && (value < NORMAL_MIN || value > NORMAL_MAX));

    if (!isAnomaly || !Number.isFinite(value)) return null;

    return (
        <circle
            cx={cx}
            cy={cy}
            r={5}
            fill="#ef4444"
            stroke="#fff"
            strokeWidth={2}
        />
    );
};

const HeartRateTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;

    const point = payload[0]?.payload ?? {};
    const value = Number(point.value);
    const hasValue = Number.isFinite(value);
    const status = getHeartRateStatus(point);
    const statusClass = status === 'Normal'
        ? 'text-green-600'
        : status === 'No reading'
            ? 'text-text-muted'
            : 'text-red-500';

    return (
        <div className="rounded-xl border border-slate-100 bg-white px-4 py-3 text-xs shadow-lg dark:border-stroke dark:bg-card">
            <p className="font-black text-text-primary dark:text-text-primary">{formatHourLabel(label)}</p>
            <p className="mt-2 font-semibold text-slate-500 dark:text-text-muted">
                Value: <span className="text-text-primary dark:text-text-primary">{hasValue ? `${value} bpm` : 'No reading'}</span>
            </p>
            <p className={`mt-1 font-black uppercase tracking-[0.16em] ${statusClass}`}>
                {status}
            </p>
        </div>
    );
};

const HeartRateChart = ({ data, height = 200 }) => {
    const safeData = safeArray(data);
    return (
        <div className="w-full" style={{ height }}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={safeData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <ReferenceArea y1={CHART_MIN} y2={NORMAL_MIN} fill="rgba(255,193,7,0.1)" strokeOpacity={0} />
                    <ReferenceArea y1={NORMAL_MIN} y2={NORMAL_MAX} fill="rgba(34,197,94,0.1)" strokeOpacity={0} />
                    <ReferenceArea y1={NORMAL_MAX} y2={CHART_MAX} fill="rgba(255,193,7,0.1)" strokeOpacity={0} />
                    <CartesianGrid strokeDasharray="4 4" stroke="#E8E8E8" vertical={false} />
                    <XAxis
                        dataKey="hour"
                        type="number"
                        domain={[0, 23]}
                        ticks={HOUR_TICKS}
                        tickFormatter={formatHourLabel}
                        interval={0}
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#BBBBBB", fontSize: 11 }}
                    />
                    <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#BBBBBB", fontSize: 11 }}
                        domain={[CHART_MIN, CHART_MAX]}
                    />
                    <Tooltip content={<HeartRateTooltip />} />
                    <Line
                        type="natural"
                        dataKey="value"
                        name="Heart Rate"
                        stroke="#FF4B26"
                        strokeWidth={2}
                        dot={renderAnomalyDot}
                        connectNulls={false}
                        isAnimationActive={true}
                        animationDuration={1200}
                        animationEasing="ease-out"
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
};

export default HeartRateChart;

