import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AppText } from '../components/AppText';
import { useTheme } from '../theme/ThemeProvider';

export function Placeholder({ title, subtitle }: { title: string; subtitle: string }) {
  const { colors, spacing } = useTheme();
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <View style={{ flex: 1, padding: spacing.xl, justifyContent: 'center', gap: spacing.s }}>
        <AppText variant="h1" tone="heading">
          {title}
        </AppText>
        <AppText variant="body" tone="body">
          {subtitle}
        </AppText>
      </View>
    </SafeAreaView>
  );
}

export const PlanScreen = () => (
  <Placeholder title="Plan" subtitle="Per-meal calorie budgets and ideas that fit what's left." />
);
