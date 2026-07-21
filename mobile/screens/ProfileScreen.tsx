import { View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { useAuth } from '../auth/AuthProvider';
import { AppText } from '../components/AppText';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { useTheme, useThemeToggle } from '../theme/ThemeProvider';

export function ProfileScreen() {
  const { email, status, logout } = useAuth();
  const toggle = useThemeToggle();
  const { colors, spacing } = useTheme();
  const isGuest = status === 'guest';

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <View style={{ flex: 1, padding: spacing.xl, gap: spacing.xl }}>
        <AppText variant="h1" tone="heading">
          Profile
        </AppText>

        <Card>
          <View style={{ gap: spacing.xs }}>
            <AppText variant="caption" tone="caption">
              {isGuest ? 'SIGNED IN AS' : 'ACCOUNT'}
            </AppText>
            <AppText variant="title" tone="heading">
              {isGuest ? 'Guest' : (email ?? '—')}
            </AppText>
            <AppText variant="secondary" tone="body">
              {isGuest
                ? 'Your history is kept only on this device.'
                : 'Daily calorie goal, units and consent settings arrive next.'}
            </AppText>
          </View>
        </Card>

        <View style={{ gap: spacing.m }}>
          <Button label="Toggle theme" variant="secondary" onPress={toggle} />
          <Button
            label={isGuest ? 'Sign in' : 'Log out'}
            variant={isGuest ? 'primary' : 'secondary'}
            onPress={() => void logout()}
          />
        </View>
      </View>
    </SafeAreaView>
  );
}
