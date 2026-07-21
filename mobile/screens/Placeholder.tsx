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

export const HomeScreen = () => (
  <Placeholder title="Home" subtitle="Your daily calorie ring and today's meals will live here." />
);
export const HistoryScreen = () => (
  <Placeholder title="History" subtitle="Past days, weekly totals, and edits to logged meals." />
);
export const ScanScreen = () => (
  <Placeholder title="Scan" subtitle="Point your camera at a plate to identify it and estimate calories." />
);
export const PlanScreen = () => (
  <Placeholder title="Plan" subtitle="Per-meal calorie budgets and ideas that fit what's left." />
);
