import {
  Pressable,
  Text,
  type PressableProps,
  type StyleProp,
  type ViewStyle,
} from 'react-native';

import { useTheme } from '../theme/ThemeProvider';

type Variant = 'primary' | 'secondary' | 'success';

interface ButtonProps extends Omit<PressableProps, 'style' | 'children'> {
  label: string;
  variant?: Variant;
  style?: StyleProp<ViewStyle>;
}

export function Button({ label, variant = 'primary', disabled, style, ...rest }: ButtonProps) {
  const { colors, radii, spacing, typography, shadows } = useTheme();
  const isSecondary = variant === 'secondary';
  const background = isSecondary
    ? colors.card
    : variant === 'success'
      ? colors.success
      : colors.primary;
  const foreground = isSecondary ? colors.primary : colors.onPrimary;

  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      style={({ pressed }) => [
        {
          backgroundColor: background,
          borderColor: isSecondary ? colors.primary : 'transparent',
          borderWidth: isSecondary ? 1.5 : 0,
          borderRadius: radii.button,
          paddingVertical: spacing.m,
          paddingHorizontal: spacing.xl,
          alignItems: 'center',
          opacity: disabled ? 0.45 : pressed ? 0.85 : 1,
        },
        !isSecondary && shadows.light,
        style,
      ]}
      {...rest}
    >
      <Text style={[typography.button, { color: foreground }]}>{label}</Text>
    </Pressable>
  );
}
