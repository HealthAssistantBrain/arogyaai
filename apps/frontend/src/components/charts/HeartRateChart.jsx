import React from 'react';
import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip
} from 'recharts';
import { safeArray } from '../../utils/safeData';

const HeartRateChart = ({ data, height = 200 }) => {
    const safeData = safeArray(data);
    return (
        <div className="w-full" style={{ height }}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={safeData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="4 4" stroke="#E8E8E8" vertical={false} />
                    <XAxis
                        dataKey="t"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#BBBBBB", fontSize: 11 }}
                    />
                    <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#BBBBBB", fontSize: 11 }}
                        domain={['auto', 'auto']}
                    />
                    <Tooltip
                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                        labelStyle={{ fontWeight: 'bold', marginBottom: '4px' }}
                    />
                    <Line
                        type="natural"
                        dataKey="v"
                        stroke="#FF4B26"
                        strokeWidth={2}
                        dot={false}
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
