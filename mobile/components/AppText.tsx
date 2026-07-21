import { Text, type TextProps } from 'react-native';

import { useTheme } from '../theme/ThemeProvider';
import type { TypographyVariant } from '../theme/tokens';

type Tone = 'heading' | 'body' | 'caption' | 'primary' | 'onPrimary' | 'sage';

interface AppTextProps extends TextProps {
  variant?: TypographyVariant;
  tone?: Tone;
}

export function AppText({ variant = 'body', tone = 'body', style, ...rest }: AppTextProps) {
  const { typography, colors } = useTheme();
  return <Text style={[typography[variant], { color: colors[tone] }, style]} {...rest} />;
}
