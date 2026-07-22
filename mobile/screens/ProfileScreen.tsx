import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, Switch, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { fetchMe, updateProfile } from '../api/auth';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import { AppText } from '../components/AppText';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { thousands } from '../lib/format';
import { useTheme, useThemeToggle } from '../theme/ThemeProvider';

const GOAL_MIN = 800;
const GOAL_MAX = 8000;
const GOAL_STEP = 50;

function clampGoal(value: number): number {
  return Math.max(GOAL_MIN, Math.min(GOAL_MAX, value));
}

// Top-level so its identity is stable across renders (no remount on each tap).
function GoalStepButton({
  label,
  accessibilityLabel,
  onPress,
}: {
  label: string;
  accessibilityLabel: string;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      style={{
        width: 44,
        height: 44,
        borderRadius: 22,
        borderWidth: 1.5,
        borderColor: colors.primary,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <AppText variant="h3" tone="primary">
        {label}
      </AppText>
    </Pressable>
  );
}

export function ProfileScreen() {
  const { email, status, accessToken, logout } = useAuth();
  const toggle = useThemeToggle();
  const { colors, spacing } = useTheme();
  const isGuest = status === 'guest';

  const [loading, setLoading] = useState(!isGuest);
  const [goal, setGoal] = useState(2000);
  const [savedGoal, setSavedGoal] = useState(2000);
  const [consent, setConsent] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken) {
      setLoading(false);
      return;
    }
    try {
      const me = await fetchMe(accessToken);
      setGoal(me.daily_calorie_goal);
      setSavedGoal(me.daily_calorie_goal);
      setConsent(me.data_consent);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load your profile.');
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    void load();
  }, [load]);

  const saveGoal = async () => {
    if (!accessToken || goal === savedGoal) return;
    setSaving(true);
    setError(null);
    try {
      const me = await updateProfile(accessToken, { daily_calorie_goal: goal });
      setSavedGoal(me.daily_calorie_goal);
      setGoal(me.daily_calorie_goal);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save your goal.");
      setGoal(savedGoal);
    } finally {
      setSaving(false);
    }
  };

  const setConsentValue = async (next: boolean) => {
    if (!accessToken) return;
    setConsent(next); // optimistic
    try {
      await updateProfile(accessToken, { data_consent: next });
    } catch {
      setConsent(!next); // revert on failure
      setError("Couldn't update your consent setting.");
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <View style={{ flex: 1, padding: spacing.xl, gap: spacing.l }}>
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
            {isGuest ? (
              <AppText variant="secondary" tone="body">
                Your history is kept only on this device.
              </AppText>
            ) : null}
          </View>
        </Card>

        {error ? (
          <AppText variant="secondary" tone="error">
            {error}
          </AppText>
        ) : null}

        {isGuest ? null : loading ? (
          <ActivityIndicator color={colors.sage} />
        ) : (
          <>
            {/* daily calorie goal */}
            <Card>
              <View style={{ gap: spacing.m }}>
                <AppText variant="caption" tone="caption">
                  DAILY CALORIE GOAL
                </AppText>
                <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                  <GoalStepButton
                    label="−"
                    accessibilityLabel="Decrease goal"
                    onPress={() => setGoal((g) => clampGoal(g - GOAL_STEP))}
                  />
                  <View style={{ alignItems: 'center' }}>
                    <AppText variant="h1" tone="heading">
                      {thousands(goal)}
                    </AppText>
                    <AppText variant="caption" tone="caption">
                      kcal / day
                    </AppText>
                  </View>
                  <GoalStepButton
                    label="+"
                    accessibilityLabel="Increase goal"
                    onPress={() => setGoal((g) => clampGoal(g + GOAL_STEP))}
                  />
                </View>
                {goal !== savedGoal ? (
                  <Button
                    label={saving ? 'Saving…' : 'Save goal'}
                    disabled={saving}
                    onPress={() => void saveGoal()}
                  />
                ) : null}
              </View>
            </Card>

            {/* data-contribution consent */}
            <Card>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.m }}>
                <View style={{ flex: 1, gap: spacing.xs }}>
                  <AppText variant="subtitle" tone="heading">
                    Help improve NutriScan
                  </AppText>
                  <AppText variant="secondary" tone="body">
                    Contribute your scans and corrections to train better models. You can turn this
                    off any time.
                  </AppText>
                </View>
                <Switch
                  value={consent}
                  onValueChange={(v) => void setConsentValue(v)}
                  trackColor={{ true: colors.sage, false: colors.border }}
                  thumbColor={colors.card}
                />
              </View>
            </Card>
          </>
        )}

        <View style={{ gap: spacing.m, marginTop: 'auto' }}>
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
