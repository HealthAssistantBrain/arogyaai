import React from 'react';

const IconBox = ({ icon: Icon, color = 'bg-primary', className = "" }) => {
    return (
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${color} bg-opacity-10 ${className}`}>
            <Icon className={`w-5 h-5 ${color.replace('bg-', 'text-')}`} />
        </div>
    );
};

export default IconBox;
