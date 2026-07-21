import { Ionicons } from '@expo/vector-icons';
import { View } from 'react-native';

import { useTheme } from '../theme/ThemeProvider';

interface BrandMarkProps {
  size?: number;
  /** On the sage splash gradient: translucent white tile + white icon. */
  onDark?: boolean;
}

export function BrandMark({ size = 64, onDark = false }: BrandMarkProps) {
  const { colors } = useTheme();
  const background = onDark ? 'rgba(255, 255, 255, 0.18)' : colors.sage;
  const iconColor = onDark ? '#FBF9F1' : colors.onSage;
  const dot = Math.round(size * 0.11);

  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: Math.round(size * 0.3),
        backgroundColor: background,
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <Ionicons name="scan-outline" size={Math.round(size * 0.54)} color={iconColor} />
      <View
        style={{
          position: 'absolute',
          width: dot,
          height: dot,
          borderRadius: dot / 2,
          backgroundColor: iconColor,
        }}
      />
    </View>
  );
}
