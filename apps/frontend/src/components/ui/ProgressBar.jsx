import React from 'react';

const ProgressBar = ({ progress, color = 'bg-primary', height = 'h-2' }) => {
    return (
        <div className={`w-full bg-[#EEEEEE] rounded-full overflow-hidden ${height}`}>
            <div
                className={`h-full ${color} rounded-full transition-all duration-1000 ease-out`}
                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
        </div>
    );
};

export default ProgressBar;
