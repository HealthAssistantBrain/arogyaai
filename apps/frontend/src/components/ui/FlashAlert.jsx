import React, { useState, useEffect } from 'react';
import { AlertCircle, CheckCircle, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const FlashAlert = ({ message, type = 'high_risk', duration = 5000, onClose }) => {
    const [isVisible, setIsVisible] = useState(true);

    useEffect(() => {
        if (duration) {
            const timer = setTimeout(() => {
                setIsVisible(false);
                if (onClose) setTimeout(onClose, 500);
            }, duration);
            return () => clearTimeout(timer);
        }
    }, [duration, onClose]);

    const configs = {
        high_risk: { bg: 'bg-danger', icon: AlertCircle },
        success: { bg: 'bg-success', icon: CheckCircle },
        warning: { bg: 'bg-warning', icon: AlertCircle },
    };

    const config = configs[type] || configs.high_risk;

    return (
        <AnimatePresence>
            {isVisible && (
                <motion.div
                    initial={{ opacity: 0, y: -20, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className={`flex items-center gap-3 p-4 rounded-2xl shadow-lg text-text-primary ${config.bg} mb-4`}
                >
                    <config.icon className="w-5 h-5 flex-shrink-0" />
                    <p className="text-sm font-bold flex-1">{message}</p>
                    <button
                        onClick={() => {
                            setIsVisible(false);
                            if (onClose) setTimeout(onClose, 500);
                        }}
                        className="p-1 hover:bg-white/20 rounded-lg transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </motion.div>
            )}
        </AnimatePresence>
    );
};

export default FlashAlert;

