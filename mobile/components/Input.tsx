import { TextInput, View, type TextInputProps } from 'react-native';

import { useTheme } from '../theme/ThemeProvider';
import { AppText } from './AppText';

interface InputProps extends TextInputProps {
  label: string;
  error?: string | null;
}

export function Input({ label, error, style, ...rest }: InputProps) {
  const { colors, radii, spacing, typography } = useTheme();
  return (
    <View style={{ gap: spacing.xs }}>
      <AppText variant="secondary" tone="body">
        {label}
      </AppText>
      <TextInput
        placeholderTextColor={colors.caption}
        style={[
          {
            backgroundColor: colors.card,
            borderColor: error ? colors.error : colors.border,
            borderWidth: 1,
            borderRadius: radii.input,
            paddingHorizontal: spacing.l,
            paddingVertical: spacing.m,
            fontSize: typography.body.fontSize,
            color: colors.heading,
          },
          style,
        ]}
        {...rest}
      />
      {error ? (
        <AppText variant="caption" style={{ color: colors.error }}>
          {error}
        </AppText>
      ) : null}
    </View>
  );
}
