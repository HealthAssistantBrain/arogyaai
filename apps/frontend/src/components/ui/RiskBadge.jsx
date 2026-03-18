import React from 'react';

const RiskBadge = ({ level, score }) => {
    const configs = {
        high: { bg: 'bg-danger/10', text: 'text-danger', label: 'High' },
        moderate: { bg: 'bg-warning/10', text: 'text-warning', label: 'Moderate' },
        low: { bg: 'bg-success/10', text: 'text-success', label: 'Low' },
    };

    const config = configs[level] || configs.low;

    return (
        <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full ${config.bg} ${config.text}`}>
            <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
            <span className="text-[11px] font-bold uppercase tracking-wider">
                {config.label} {score && `• ${score}%`}
            </span>
        </div>
    );
};

export default RiskBadge;
