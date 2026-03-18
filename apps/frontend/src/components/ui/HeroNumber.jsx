import React from 'react';

const HeroNumber = ({ value, unit, label, className = "" }) => {
    return (
        <div className={`flex flex-col ${className}`}>
            <div className="flex items-baseline gap-1">
                <span className="hero-number font-number">{value}</span>
                {unit && <span className="text-text-muted text-sm font-bold uppercase tracking-wide">{unit}</span>}
            </div>
            {label && <span className="text-text-secondary text-xs font-medium uppercase tracking-wider">{label}</span>}
        </div>
    );
};

export default HeroNumber;
