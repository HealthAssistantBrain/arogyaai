import React from 'react';

const Input = ({ label, error, ...props }) => {
    return (
        <div className="flex flex-col gap-1.5 w-full">
            {label && <label className="text-[11px] font-bold uppercase tracking-wider text-text-muted px-1">{label}</label>}
            <input
                className={`w-full bg-white border-2 border-[#EEEEEE] rounded-xl px-4 py-3 text-sm font-medium focus:border-primary focus:outline-none transition-all ${error ? 'border-danger' : ''}`}
                {...props}
            />
            {error && <span className="text-[11px] text-danger font-bold px-1">{error}</span>}
        </div>
    );
};

export default Input;
