import { useEffect } from 'react';
import { useThemeStore } from '../store/themeStore';

export const useThemeEffect = () => {
    const theme = useThemeStore((state) => state.theme);
    const initializeTheme = useThemeStore((state) => state.initializeTheme);
    const syncThemeWithSystem = useThemeStore((state) => state.syncThemeWithSystem);

    useEffect(() => {
        initializeTheme();
    }, [initializeTheme]);

    useEffect(() => {
        syncThemeWithSystem();
    }, [theme, syncThemeWithSystem]);

    useEffect(() => {
        if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
            return undefined;
        }

        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

        const handleSystemThemeChange = () => {
            if (useThemeStore.getState().theme === 'system') {
                useThemeStore.getState().syncThemeWithSystem();
            }
        };

        if (typeof mediaQuery.addEventListener === 'function') {
            mediaQuery.addEventListener('change', handleSystemThemeChange);
            return () => mediaQuery.removeEventListener('change', handleSystemThemeChange);
        }

        mediaQuery.addListener(handleSystemThemeChange);
        return () => mediaQuery.removeListener(handleSystemThemeChange);
    }, []);
};
