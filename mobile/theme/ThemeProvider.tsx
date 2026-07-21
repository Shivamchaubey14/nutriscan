/** Theme context: resolves light/dark (system default, with a manual toggle). */
import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useColorScheme } from 'react-native';

import {
  darkPalette,
  lightPalette,
  radii,
  shadows,
  spacing,
  typography,
  type Palette,
} from './tokens';

export interface Theme {
  colors: Palette;
  spacing: typeof spacing;
  radii: typeof radii;
  shadows: typeof shadows;
  typography: typeof typography;
  isDark: boolean;
}

interface ThemeContextValue {
  theme: Theme;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systemScheme = useColorScheme();
  const [override, setOverride] = useState<'light' | 'dark' | null>(null);
  const isDark = (override ?? systemScheme ?? 'light') === 'dark';

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme: {
        colors: isDark ? darkPalette : lightPalette,
        spacing,
        radii,
        shadows,
        typography,
        isDark,
      },
      toggle: () => setOverride(isDark ? 'light' : 'dark'),
    }),
    [isDark]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

function useThemeContext(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

export const useTheme = (): Theme => useThemeContext().theme;
export const useThemeToggle = (): (() => void) => useThemeContext().toggle;
