import { useId, useMemo } from 'react';
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from 'recharts';
import { getComparableMetricValue } from '../../utils/metricsRules';
import { safeArray } from '../../utils/safeData';

const MiniSparkline = ({ data = [], metric, color = '#64748b' }) => {
  const gradientId = useId().replace(/:/g, '');
  const points = useMemo(
    () => safeArray(data)
      .slice(-24)
      .map((item, index) => ({
        index,
        value: getComparableMetricValue(metric, item?.value ?? item?.systolic ?? item),
      }))
      .filter((item) => item.value !== null),
    [data, metric]
  );

  if (points.length < 2) return null;

  return (
    <ResponsiveContainer width="100%" height={42}>
      <AreaChart data={points} margin={{ top: 5, right: 2, bottom: 3, left: 2 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.2} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <XAxis dataKey="index" hide />
        <YAxis hide domain={['dataMin', 'dataMax']} />
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2.5}
          fill={`url(#${gradientId})`}
          fillOpacity={1}
          dot={false}
          activeDot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
};

export default MiniSparkline;

