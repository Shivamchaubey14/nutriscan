import { View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

import { thousands } from '../lib/format';
import { useTheme } from '../theme/ThemeProvider';
import { AppText } from './AppText';

interface Props {
  consumed: number;
  goal: number;
  size?: number;
  strokeWidth?: number;
}

/** Circular progress of calories consumed vs the daily goal. Turns tan once over. */
export function CalorieRing({ consumed, goal, size = 132, strokeWidth = 12 }: Props) {
  const { colors } = useTheme();
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const ratio = goal > 0 ? consumed / goal : 0;
  const progress = Math.max(0, Math.min(1, ratio));
  const over = ratio > 1;
  const track = colors.sageSoft;
  const fill = over ? colors.accent : colors.sage;

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute' }}>
        <Circle cx={size / 2} cy={size / 2} r={radius} stroke={track} strokeWidth={strokeWidth} fill="none" />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={fill}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={`${circumference * progress} ${circumference}`}
          // Start the arc at 12 o'clock and sweep clockwise.
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </Svg>
      <AppText variant="h2" tone="heading">
        {thousands(consumed)}
      </AppText>
      <AppText variant="caption" tone="caption">
        of {thousands(goal)} kcal
      </AppText>
    </View>
  );
}
