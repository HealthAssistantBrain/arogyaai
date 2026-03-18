/**
 * Framer Motion Animation Variants for ArogyaAI
 */

export const pageTransition = {
    initial: { opacity: 0, y: 18 },
    animate: {
        opacity: 1,
        y: 0,
        transition: {
            duration: 0.32,
            ease: [0.22, 1, 0.36, 1]
        }
    },
    exit: {
        opacity: 0,
        y: -12,
        transition: {
            duration: 0.2
        }
    }
};

export const staggerContainer = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: {
            staggerChildren: 0.07
        }
    }
};

export const staggerItem = {
    hidden: { opacity: 0, y: 20 },
    visible: {
        opacity: 1,
        y: 0,
        transition: {
            duration: 0.4,
            ease: [0.22, 1, 0.36, 1]
        }
    }
};

export const cardHover = {
    rest: { y: 0, boxShadow: "0 2px 16px rgba(0,0,0,0.06)" },
    hover: {
        y: -4,
        boxShadow: "0 8px 28px rgba(0,0,0,0.12)",
        transition: {
            duration: 0.2,
            ease: "easeOut"
        }
    }
};
