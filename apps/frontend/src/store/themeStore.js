import { create } from 'zustand';

export const THEME_STORAGE_KEY = 'theme';
const THEMES = ['light', 'dark', 'system'];

const isBrowser = () => typeof window !== 'undefined';

export const getStoredTheme = () => {
    if (!isBrowser()) return 'system';

    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    return THEMES.includes(storedTheme) ? storedTheme : 'system';
};

export const getSystemTheme = () => {
    if (!isBrowser() || typeof window.matchMedia !== 'function') return 'light';

    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
};

export const resolveTheme = (theme) => {
    if (theme === 'system') {
        return getSystemTheme();
    }

    return theme === 'dark' ? 'dark' : 'light';
};

export const applyThemePreference = (theme) => {
    if (!isBrowser()) return resolveTheme(theme);

    const root = document.documentElement;
    const resolvedTheme = resolveTheme(theme);

    root.classList.toggle('dark', resolvedTheme === 'dark');
    root.style.colorScheme = resolvedTheme;

    return resolvedTheme;
};

export const bootstrapTheme = () => {
    const theme = getStoredTheme();
    const resolvedTheme = applyThemePreference(theme);

    useThemeStore.setState({ theme, resolvedTheme });

    return { theme, resolvedTheme };
};

export const useThemeStore = create((set, get) => ({
    theme: 'system',
    resolvedTheme: 'light',

    setTheme: (theme) => {
        const nextTheme = THEMES.includes(theme) ? theme : 'system';

        if (isBrowser()) {
            window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
        }

        set({
            theme: nextTheme,
            resolvedTheme: applyThemePreference(nextTheme),
        });
    },

    syncThemeWithSystem: () => {
        const currentTheme = get().theme;

        set({
            resolvedTheme: applyThemePreference(currentTheme),
        });
    },

    initializeTheme: () => {
        const theme = getStoredTheme();

        set({
            theme,
            resolvedTheme: applyThemePreference(theme),
        });
    },
}));
