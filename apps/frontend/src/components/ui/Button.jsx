import React from 'react';

const Button = ({
    children,
    variant = 'primary',
    size = 'md',
    className = "",
    ...props
}) => {
    const variants = {
        primary: 'bg-primary text-white hover:bg-opacity-90 shadow-sm',
        accent: 'bg-accent text-white hover:bg-opacity-90 shadow-sm',
        outline: 'border-2 border-stroke bg-card text-text-secondary hover:bg-surface-muted',
        ghost: 'text-text-secondary hover:bg-surface-muted',
        danger: 'bg-danger text-white hover:bg-opacity-90 shadow-sm',
    };

    const sizes = {
        sm: 'px-3 py-1.5 text-xs',
        md: 'px-4 py-2 text-sm',
        lg: 'px-6 py-3 text-base',
    };

    return (
        <button
            className={`rounded-xl font-bold transition-all duration-200 active:scale-95 disabled:opacity-50 ${variants[variant]} ${sizes[size]} ${className}`}
            {...props}
        >
            {children}
        </button>
    );
};

export default Button;
