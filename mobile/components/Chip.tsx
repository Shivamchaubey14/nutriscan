import { View, Text } from 'react-native';

import { useTheme } from '../theme/ThemeProvider';

type Variant = 'high' | 'medium' | 'low' | 'neutral';

interface ChipProps {
  label: string;
  variant?: Variant;
}

export function Chip({ label, variant = 'neutral' }: ChipProps) {
  const { colors, radii, spacing, typography } = useTheme();
  const dot = {
    high: colors.success,
    medium: colors.warning,
    low: colors.error,
    neutral: colors.caption,
  }[variant];

  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        alignSelf: 'flex-start',
        gap: spacing.xs,
        backgroundColor: dot + '22', // soft tint; text stays heading-colored for AA contrast
        borderRadius: radii.chip,
        paddingVertical: spacing.xs,
        paddingHorizontal: spacing.m,
      }}
    >
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: dot }} />
      <Text style={[typography.caption, { color: colors.heading }]}>{label}</Text>
    </View>
  );
}
