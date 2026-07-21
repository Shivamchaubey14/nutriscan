import { Text, View } from 'react-native';

import { useTheme } from '../theme/ThemeProvider';

type Variant = 'high' | 'medium' | 'low' | 'neutral';

interface ChipProps {
  label: string;
  variant?: Variant;
}

export function Chip({ label, variant = 'neutral' }: ChipProps) {
  const { colors, radii, spacing, typography } = useTheme();
  const style = {
    high: { bg: colors.sageSoft, fg: colors.onSage },
    medium: { bg: colors.accentSoft, fg: colors.onAccent },
    low: { bg: colors.errorSoft, fg: colors.error },
    neutral: { bg: colors.cardMuted, fg: colors.caption },
  }[variant];

  return (
    <View
      style={{
        alignSelf: 'flex-start',
        backgroundColor: style.bg,
        borderRadius: radii.chip,
        paddingVertical: spacing.xs,
        paddingHorizontal: spacing.m,
      }}
    >
      <Text style={[typography.caption, { color: style.fg }]}>{label}</Text>
    </View>
  );
}
