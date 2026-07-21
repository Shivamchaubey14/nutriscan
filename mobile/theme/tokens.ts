/**
 * Design tokens — the warm sage-green & cream system, sampled from the canonical
 * screen mockups (docs/design/). Two greens carry the identity: a deep olive for
 * buttons/primary actions, and a lighter sage for the scan FAB, progress rings
 * and high-confidence. Tan (+ soft tan) handles over-goal and source badges.
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
    shadowColor: '#2F3427',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 3,
  },
  medium: {
    shadowColor: '#2F3427',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.14,
    shadowRadius: 22,
    elevation: 6,
  },
  large: {
    shadowColor: '#2F3427',
    shadowOffset: { width: 0, height: 20 },
    shadowOpacity: 0.18,
    shadowRadius: 40,
    elevation: 12,
  },
};

export interface Palette {
  background: string;
  card: string;
  cardMuted: string;
  border: string;
  heading: string;
  body: string;
  caption: string;
  primary: string; // deep olive — buttons, primary actions
  onPrimary: string;
  sage: string; // lighter sage — FAB, progress ring, high confidence
  sageSoft: string; // fills: high chip, within-goal bars
  onSage: string;
  accent: string; // tan — over goal, medium confidence
  accentSoft: string; // fills: source badges, medium chip
  onAccent: string;
  error: string; // terracotta — low confidence, failures
  errorSoft: string;
  olive: string; // dark camera/olive surfaces
}

export const lightPalette: Palette = {
  background: '#F4EEE1',
  card: '#FFFDF7',
  cardMuted: '#EDE6D6',
  border: '#E7E0D0',
  heading: '#2F3427',
  body: '#6C6B5E',
  caption: '#9C978A',
  primary: '#6E7C58',
  onPrimary: '#FBF9F1',
  sage: '#8CA079',
  sageSoft: '#D8E1C9',
  onSage: '#2F3427',
  accent: '#C6A06B',
  accentSoft: '#EBDBC0',
  onAccent: '#5A4A2E',
  error: '#C97B5D',
  errorSoft: '#F1DACE',
  olive: '#3B4433',
};

export const darkPalette: Palette = {
  background: '#1F241B',
  card: '#2A3125',
  cardMuted: '#333B2C',
  border: '#3C4433',
  heading: '#F1EEE3',
  body: '#C6C4B4',
  caption: '#8E8B7C',
  primary: '#8CA079',
  onPrimary: '#1B2016',
  sage: '#9DB187',
  sageSoft: '#3A4630',
  onSage: '#F1EEE3',
  accent: '#D2AE7C',
  accentSoft: '#463B27',
  onAccent: '#F1EEE3',
  error: '#D68C6E',
  errorSoft: '#4A342B',
  olive: '#2A3125',
};
