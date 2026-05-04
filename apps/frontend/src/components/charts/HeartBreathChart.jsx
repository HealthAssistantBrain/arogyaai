import React from 'react';
import {
    ResponsiveContainer,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend
} from 'recharts';

const HeartBreathChart = ({ data, height = 220 }) => {
    return (
        <div className="w-full" style={{ height }}>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="4 4" stroke="#E8E8E8" vertical={false} />
                    <XAxis
                        dataKey="t"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#BBBBBB", fontSize: 11 }}
                    />
                    <YAxis
                        yAxisId="left"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#BBBBBB", fontSize: 11 }}
                        domain={['auto', 'auto']}
                    />
                    <YAxis
                        yAxisId="right"
                        orientation="right"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#BBBBBB", fontSize: 11 }}
                        domain={['auto', 'auto']}
                    />
                    <Tooltip
                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                    />
                    <Legend
                        verticalAlign="top"
                        align="right"
                        iconType="circle"
                        wrapperStyle={{ fontSize: '10px', paddingBottom: '10px' }}
                    />
                    <Line
                        yAxisId="left"
                        type="monotone"
                        dataKey="hr"
                        name="Heart Rate"
                        stroke="#FF4B26"
                        strokeWidth={2}
                        dot={false}
                        isAnimationActive={true}
                    />
                    <Line
                        yAxisId="right"
                        type="monotone"
                        dataKey="br"
                        name="Breath Rate"
                        stroke="#1ECAD3"
                        strokeWidth={2}
                        dot={false}
                        isAnimationActive={true}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
};

export default HeartBreathChart;

