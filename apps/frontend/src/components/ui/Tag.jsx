import React from 'react';

const Tag = ({ children, variant = 'gray' }) => {
    const variants = {
        gray: 'bg-[#EEEEEE] text-text-secondary',
        blue: 'bg-primary/10 text-primary',
        teal: 'bg-accent/10 text-accent',
        orange: 'bg-danger/10 text-danger',
    };

    return (
        <span className={`px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-wider ${variants[variant]}`}>
            {children}
        </span>
    );
};

export default Tag;

