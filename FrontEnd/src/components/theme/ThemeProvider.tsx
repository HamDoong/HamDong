import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

type ThemeMode = 'light' | 'dark';
type ThemeTransitionOrigin = { x: number; y: number };
type ThemeChangeOptions = { origin?: ThemeTransitionOrigin };
type ViewTransition = {
  ready: Promise<void>;
  finished: Promise<void>;
};

type ThemeContextValue = {
  theme: ThemeMode;
  isDark: boolean;
  toggleTheme: (options?: ThemeChangeOptions) => void;
  setTheme: (theme: ThemeMode, options?: ThemeChangeOptions) => void;
};

const THEME_STORAGE_KEY = 'hamdong-theme';
const THEME_SOURCE_STORAGE_KEY = 'hamdong-theme-source';
const MANUAL_THEME_SOURCE = 'manual';
const ThemeContext = createContext<ThemeContextValue | null>(null);

function isThemeMode(theme: string | null): theme is ThemeMode {
  return theme === 'light' || theme === 'dark';
}

function getStoredTheme(): ThemeMode | null {
  if (typeof window === 'undefined') return null;

  const storedSource = window.localStorage.getItem(THEME_SOURCE_STORAGE_KEY);
  const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
  if (storedSource === MANUAL_THEME_SOURCE && isThemeMode(storedTheme)) return storedTheme;

  return null;
}

function getSystemTheme(): ThemeMode {
  if (typeof window === 'undefined') return 'light';

  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function getPreferredTheme(): ThemeMode {
  return getStoredTheme() ?? getSystemTheme();
}

function applyTheme(theme: ThemeMode) {
  const root = document.documentElement;
  root.classList.toggle('dark', theme === 'dark');
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
}

function getDefaultOrigin(): ThemeTransitionOrigin {
  return {
    x: window.innerWidth - 56,
    y: 56,
  };
}

function getTransitionRadius(origin: ThemeTransitionOrigin) {
  return Math.hypot(
    Math.max(origin.x, window.innerWidth - origin.x),
    Math.max(origin.y, window.innerHeight - origin.y),
  );
}

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function runFallbackThemeTransition(
  nextTheme: ThemeMode,
  origin: ThemeTransitionOrigin,
  commitTheme: () => void,
) {
  const overlay = document.createElement('div');
  overlay.className = `theme-transition-fallback theme-transition-fallback-${nextTheme}`;
  overlay.style.setProperty('--theme-transition-x', `${origin.x}px`);
  overlay.style.setProperty('--theme-transition-y', `${origin.y}px`);
  overlay.style.setProperty('--theme-transition-radius', `${getTransitionRadius(origin)}px`);
  document.body.appendChild(overlay);

  window.requestAnimationFrame(() => {
    overlay.classList.add('is-expanding');
  });

  window.setTimeout(() => {
    commitTheme();
    overlay.classList.add('is-settling');
  }, 460);

  window.setTimeout(() => {
    overlay.remove();
  }, 760);
}

function runThemeTransition(
  nextTheme: ThemeMode,
  options: ThemeChangeOptions | undefined,
  commitTheme: () => void,
) {
  if (typeof window === 'undefined' || prefersReducedMotion()) {
    commitTheme();
    return;
  }

  const origin = options?.origin ?? getDefaultOrigin();
  const root = document.documentElement;
  const startViewTransition = (
    document as Document & {
      startViewTransition?: (callback: () => void) => ViewTransition;
    }
  ).startViewTransition;

  if (!startViewTransition) {
    runFallbackThemeTransition(nextTheme, origin, commitTheme);
    return;
  }

  root.classList.add('theme-transitioning');
  root.style.setProperty('--theme-transition-x', `${origin.x}px`);
  root.style.setProperty('--theme-transition-y', `${origin.y}px`);
  root.style.setProperty('--theme-transition-radius', `${getTransitionRadius(origin)}px`);

  const transition = startViewTransition.call(document, () => {
    commitTheme();
  });

  void transition.ready.then(() => {
    root.animate(
      {
        clipPath: [
          `circle(0px at ${origin.x}px ${origin.y}px)`,
          `circle(${getTransitionRadius(origin)}px at ${origin.x}px ${origin.y}px)`,
        ],
      },
      {
        duration: 760,
        easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
        pseudoElement: '::view-transition-new(root)',
      } as KeyframeAnimationOptions,
    );
  });

  void transition.finished.finally(() => {
    root.classList.remove('theme-transitioning');
    root.style.removeProperty('--theme-transition-x');
    root.style.removeProperty('--theme-transition-y');
    root.style.removeProperty('--theme-transition-radius');
  });
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>(() => getPreferredTheme());
  const [hasStoredPreference, setHasStoredPreference] = useState(() => getStoredTheme() !== null);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (hasStoredPreference) return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const syncSystemTheme = (event: MediaQueryListEvent | MediaQueryList) => {
      setThemeState(event.matches ? 'dark' : 'light');
    };

    syncSystemTheme(mediaQuery);

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', syncSystemTheme);
      return () => mediaQuery.removeEventListener('change', syncSystemTheme);
    }

    mediaQuery.addListener(syncSystemTheme);
    return () => mediaQuery.removeListener(syncSystemTheme);
  }, [hasStoredPreference]);

  const value = useMemo<ThemeContextValue>(() => {
    const commitTheme = (nextTheme: ThemeMode) => {
      applyTheme(nextTheme);
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
      window.localStorage.setItem(THEME_SOURCE_STORAGE_KEY, MANUAL_THEME_SOURCE);
      setHasStoredPreference(true);
      setThemeState(nextTheme);
    };

    const setTheme = (nextTheme: ThemeMode, options?: ThemeChangeOptions) => {
      if (nextTheme === theme) return;
      runThemeTransition(nextTheme, options, () => commitTheme(nextTheme));
    };

    return {
      theme,
      isDark: theme === 'dark',
      setTheme,
      toggleTheme: (options?: ThemeChangeOptions) => {
        const nextTheme = theme === 'dark' ? 'light' : 'dark';
        runThemeTransition(nextTheme, options, () => commitTheme(nextTheme));
      },
    };
  }, [theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return context;
}
