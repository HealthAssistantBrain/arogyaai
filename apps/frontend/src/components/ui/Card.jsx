import React from 'react';
import { motion } from 'framer-motion';
import { cardHover } from '../../styles/animations';

const Card = ({ children, className = "", noPadding = false, animate = true }) => {
    const Component = animate ? motion.div : 'div';
    const animationProps = animate ? {
        initial: "rest",
        whileHover: "hover",
        variants: cardHover
    } : {};

    return (
        <Component
            {...animationProps}
            className={`card-container ${noPadding ? 'p-0' : 'p-5'} ${className}`}
        >
            {children}
        </Component>
    );
};

export default Card;
