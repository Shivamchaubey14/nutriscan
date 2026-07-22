import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '../api/client';
import { fetchLogs, fetchSummary, type DailySummary, type MealLog } from '../api/log';
import { useAuth } from '../auth/AuthProvider';
import { AppText } from '../components/AppText';
import { Button } from '../components/Button';
import { CalorieRing } from '../components/CalorieRing';
import { displayName, initial, longDate, shortTime, thousands, titleCase } from '../lib/format';
import type { MainTabParamList } from '../navigation/types';
import { useTheme } from '../theme/ThemeProvider';

// Macro goals aren't stored per-user yet, so derive them from the calorie goal
// with a conventional 20 / 50 / 30 protein / carb / fat energy split.
function macroGoals(calorieGoal: number) {
  return {
    protein: Math.round((calorieGoal * 0.2) / 4),
    carbs: Math.round((calorieGoal * 0.5) / 4),
    fat: Math.round((calorieGoal * 0.3) / 9),
  };
}

function MacroBar({ label, value, goal }: { label: string; value: number; goal: number }) {
  const { colors, spacing } = useTheme();
  const pct = goal > 0 ? Math.min(1, value / goal) : 0;
  return (
    <View style={{ gap: spacing.xs }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
        <AppText variant="secondary" tone="body">
          {label}
        </AppText>
        <AppText variant="secondary" tone="caption">
          {Math.round(value)} / {goal} g
        </AppText>
      </View>
      <View style={{ height: 6, borderRadius: 3, backgroundColor: colors.cardMuted, overflow: 'hidden' }}>
        <View
          style={{ width: `${pct * 100}%`, height: '100%', borderRadius: 3, backgroundColor: colors.sage }}
        />
      </View>
    </View>
  );
}

export function HomeScreen() {
  const { colors, spacing, radii, shadows } = useTheme();
  const { accessToken, email, status } = useAuth();
  const navigation = useNavigation<BottomTabNavigationProp<MainTabParamList>>();
  const [summary, setSummary] = useState<DailySummary | null>(null);
  const [meals, setMeals] = useState<MealLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!accessToken) {
      setLoading(false);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const nextSummary = await fetchSummary(accessToken);
      const nextMeals = await fetchLogs(accessToken, nextSummary.date);
      setSummary(nextSummary);
      setMeals(nextMeals);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load your day.');
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  if (status === 'guest') {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
        <View style={{ flex: 1, padding: spacing.xl, justifyContent: 'center', gap: spacing.m }}>
          <AppText variant="h2" tone="heading">
            Track your day
          </AppText>
          <AppText variant="body" tone="body">
            Sign in to see your calorie ring and daily totals.
          </AppText>
        </View>
      </SafeAreaView>
    );
  }

  const goal = summary?.goal ?? 2000;
  const consumed = summary?.total_kcal ?? 0;
  const remaining = summary?.remaining ?? goal;
  const goals = macroGoals(goal);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }} edges={['top']}>
      <ScrollView
        contentContainerStyle={{ padding: spacing.xl, gap: spacing.l }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={() => void load()} tintColor={colors.sage} />}
      >
        {/* greeting */}
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View>
            <AppText variant="caption" tone="caption">
              {longDate(new Date())}
            </AppText>
            <AppText variant="h1" tone="heading">
              Hi, {displayName(email)}
            </AppText>
          </View>
          <View
            style={{
              width: 44,
              height: 44,
              borderRadius: 22,
              backgroundColor: colors.sage,
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <AppText variant="subtitle" style={{ color: colors.onSage }}>
              {initial(email)}
            </AppText>
          </View>
        </View>

        {error ? (
          <View style={{ gap: spacing.s }}>
            <AppText variant="body" tone="body">
              {error}
            </AppText>
            <Button label="Retry" variant="secondary" onPress={() => void load()} />
          </View>
        ) : null}

        {/* ring + macros */}
        <View
          style={[
            {
              backgroundColor: colors.card,
              borderRadius: radii.card,
              padding: spacing.l,
              flexDirection: 'row',
              alignItems: 'center',
              gap: spacing.l,
            },
            shadows.light,
          ]}
        >
          <CalorieRing consumed={consumed} goal={goal} />
          <View style={{ flex: 1, gap: spacing.m }}>
            <MacroBar label="Protein" value={summary?.protein_g ?? 0} goal={goals.protein} />
            <MacroBar label="Carbs" value={summary?.carbs_g ?? 0} goal={goals.carbs} />
            <MacroBar label="Fat" value={summary?.fat_g ?? 0} goal={goals.fat} />
          </View>
        </View>

        {/* today's meals */}
        <View style={{ flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' }}>
          <AppText variant="h3" tone="heading">
            Today&apos;s meals
          </AppText>
          <AppText variant="secondary" tone="caption">
            {thousands(Math.max(0, remaining))} kcal left
          </AppText>
        </View>

        {loading && !summary ? (
          <ActivityIndicator color={colors.sage} style={{ marginVertical: spacing.l }} />
        ) : meals.length === 0 ? (
          <AppText variant="body" tone="body">
            Nothing logged yet today. Scan a meal to get started.
          </AppText>
        ) : (
          meals.map((meal) => (
            <View
              key={meal.id}
              style={[
                {
                  backgroundColor: colors.card,
                  borderRadius: radii.card,
                  padding: spacing.l,
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: spacing.m,
                },
                shadows.light,
              ]}
            >
              <View
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: 20,
                  backgroundColor: colors.sageSoft,
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <AppText variant="subtitle" tone="heading">
                  {titleCase(meal.label).charAt(0)}
                </AppText>
              </View>
              <View style={{ flex: 1 }}>
                <AppText variant="subtitle" tone="heading">
                  {titleCase(meal.label)}
                </AppText>
                <AppText variant="caption" tone="caption">
                  {shortTime(meal.logged_at)}
                </AppText>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <AppText variant="subtitle" tone="heading">
                  {meal.kcal}
                </AppText>
                <AppText variant="caption" tone="sage">
                  kcal
                </AppText>
              </View>
            </View>
          ))
        )}

        {/* scan CTA */}
        <Pressable
          onPress={() => navigation.navigate('Scan')}
          style={{
            borderWidth: 1.5,
            borderColor: colors.border,
            borderStyle: 'dashed',
            borderRadius: radii.card,
            paddingVertical: spacing.l,
            alignItems: 'center',
          }}
        >
          <AppText variant="button" tone="primary">
            + Scan your next meal
          </AppText>
        </Pressable>
      </ScrollView>
    </SafeAreaView>
  );
}
