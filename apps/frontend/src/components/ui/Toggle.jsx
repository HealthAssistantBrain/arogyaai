import React from 'react';

const Toggle = ({ active, label, onChange }) => {
    return (
        <label className="flex items-center justify-between gap-4 cursor-pointer group">
            {label && <span className="text-sm font-bold text-text-primary">{label}</span>}
            <div
                onClick={() => onChange?.(!active)}
                className={`relative w-12 h-6 rounded-full border transition-colors duration-200 ease-in-out ${active ? 'border-primary bg-primary' : 'border-stroke bg-surface-muted'}`}
            >
                <div
                    className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-200 ease-in-out ${active ? 'translate-x-6' : 'translate-x-0'}`}
                />
            </div>
        </label>
    );
};

export default Toggle;

