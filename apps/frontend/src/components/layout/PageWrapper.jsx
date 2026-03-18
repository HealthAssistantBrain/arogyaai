import React from 'react';
import { motion } from 'framer-motion';
import { pageTransition } from '../../styles/animations';

const PageWrapper = ({ children }) => {
    return (
        <motion.div
            initial="initial"
            animate="animate"
            exit="exit"
            variants={pageTransition}
            className="w-full flex flex-col gap-6"
        >
            {children}
        </motion.div>
    );
};

export default PageWrapper;
