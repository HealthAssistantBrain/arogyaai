import React from 'react';
import { motion } from 'framer-motion';

const RiskGauge = ({ score, level = 'moderate', className = "" }) => {
    const radius = 40;
    const circumference = 2 * Math.PI * radius;
    const percentage = score / 100;
    const arcLength = circumference * 0.75; // 3/4 circle
    const strokeDasharray = `${arcLength} ${circumference}`;
    const strokeDashoffset = arcLength * (1 - percentage);

    const colors = {
        high: "#FF4B26",
        moderate: "#F6AD55",
        low: "#00C48C"
    };

    const color = colors[level] || colors.moderate;

    return (
        <div className={`relative flex flex-col items-center justify-center ${className}`}>
            <svg className="w-32 h-32 transform -rotate-[225deg]">
                {/* Background Track */}
                <circle
                    cx="64"
                    cy="64"
                    r={radius}
                    fill="transparent"
                    stroke="#E8E8E8"
                    strokeWidth="8"
                    strokeLinecap="round"
                    style={{ strokeDasharray }}
                />
                {/* Progress Arc */}
                <motion.circle
                    cx="64"
                    cy="64"
                    r={radius}
                    fill="transparent"
                    stroke={color}
                    strokeWidth="10"
                    strokeLinecap="round"
                    initial={{ strokeDashoffset: arcLength }}
                    animate={{ strokeDashoffset }}
                    transition={{ duration: 1.5, ease: "easeOut" }}
                    style={{ strokeDasharray }}
                />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
                <span className="text-3xl font-extrabold font-number text-text-primary">{score}</span>
                <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted">Risk Score</span>
            </div>
        </div>
    );
};

export default RiskGauge;
