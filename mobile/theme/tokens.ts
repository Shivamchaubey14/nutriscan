/**
 * Design tokens — the warm sage-green & cream system (docs/design/DESIGN.md),
 * with the type scale, spacing, radii and shadows from SRS §8.
 */
import type { TextStyle, ViewStyle } from 'react-native';

export const spacing = {
  xs: 4,
  s: 8,
  m: 12,
  l: 16,
  xl: 24,
  xxl: 32,
  section: 48,
} as const;

export const radii = {
  chip: 12,
  button: 16,
  card: 20,
  sheet: 28,
  search: 18,
  input: 16,
} as const;

export type TypographyVariant =
  | 'display'
  | 'h1'
  | 'h2'
  | 'h3'
  | 'title'
  | 'subtitle'
  | 'body'
  | 'secondary'
  | 'caption'
  | 'button';

export const typography: Record<TypographyVariant, TextStyle> = {
  display: { fontSize: 40, fontWeight: '700' },
  h1: { fontSize: 32, fontWeight: '700' },
  h2: { fontSize: 26, fontWeight: '600' },
  h3: { fontSize: 22, fontWeight: '600' },
  title: { fontSize: 18, fontWeight: '600' },
  subtitle: { fontSize: 16, fontWeight: '500' },
  body: { fontSize: 16, fontWeight: '400' },
  secondary: { fontSize: 14, fontWeight: '400' },
  caption: { fontSize: 12, fontWeight: '500' },
  button: { fontSize: 16, fontWeight: '600' },
};

export type ShadowLevel = 'light' | 'medium' | 'large';

export const shadows: Record<ShadowLevel, ViewStyle> = {
  light: {
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  medium: {
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.12,
    shadowRadius: 25,
    elevation: 6,
  },
  large: {
    shadowColor: '#0F172A',
    shadowOffset: { width: 0, height: 20 },
    shadowOpacity: 0.16,
    shadowRadius: 40,
    elevation: 12,
  },
};

export interface Palette {
  background: string;
  card: string;
  border: string;
  heading: string;
  body: string;
  caption: string;
  primary: string;
  primaryMuted: string;
  onPrimary: string;
  accent: string;
  onAccent: string;
  success: string;
  warning: string;
  error: string;
  olive: string;
}

export const lightPalette: Palette = {
  background: '#F4EEE1',
  card: '#FFFDF6',
  border: '#E8E1D2',
  heading: '#35392E',
  body: '#6B6A5E',
  caption: '#A8A395',
  primary: '#8A9B7D',
  primaryMuted: '#AEBB9C',
  onPrimary: '#FFFDF6',
  accent: '#C9A16B',
  onAccent: '#35392E',
  success: '#8A9B7D',
  warning: '#C9A16B',
  error: '#C97B5D',
  olive: '#3B4433',
};

export const darkPalette: Palette = {
  background: '#20261C',
  card: '#2C3326',
  border: '#3B4333',
  heading: '#F2EFE4',
  body: '#C7C4B5',
  caption: '#8C8A7B',
  primary: '#A9BB95',
  primaryMuted: '#7E8E6F',
  onPrimary: '#20261C',
  accent: '#D2AE7C',
  onAccent: '#20261C',
  success: '#A9BB95',
  warning: '#D2AE7C',
  error: '#D5896B',
  olive: '#3B4433',
};
