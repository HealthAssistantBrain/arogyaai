import React from 'react';
import {
    ResponsiveContainer,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend
} from 'recharts';
import { safeArray } from '../../utils/safeData';

const SleepStackedChart = ({ data = [], height = 240 }) => {
    const safeData = safeArray(data);
    return (
        <div className="w-full" style={{ height }}>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart
                    data={safeData}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                    barGap={0}
                >
                    <CartesianGrid strokeDasharray="4 4" stroke="#E8E8E8" vertical={false} />
                    <XAxis
                        dataKey="day"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#BBBBBB", fontSize: 11 }}
                    />
                    <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: "#BBBBBB", fontSize: 11 }}
                        unit="h"
                    />
                    <Tooltip
                        cursor={{ fill: '#F5F5F5' }}
                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                    />
                    <Legend
                        verticalAlign="bottom"
                        align="left"
                        iconType="circle"
                        wrapperStyle={{ fontSize: '10px', paddingTop: '10px' }}
                    />
                    <Bar dataKey="deep" stackId="a" fill="#4B6BF5" radius={[0, 0, 0, 0]} isAnimationActive={true} />
                    <Bar dataKey="light" stackId="a" fill="#FFB800" radius={[0, 0, 0, 0]} isAnimationActive={true} />
                    <Bar dataKey="rem" stackId="a" fill="#00C48C" radius={[0, 0, 0, 0]} isAnimationActive={true} />
                    <Bar dataKey="awake" stackId="a" fill="#FF4B26" radius={[4, 4, 0, 0]} isAnimationActive={true} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
};

export default SleepStackedChart;

