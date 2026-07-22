import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '../api/client';
import { deleteLog, fetchLogs, fetchSummary, type MealLog } from '../api/log';
import { useAuth } from '../auth/AuthProvider';
import { AppText } from '../components/AppText';
import { Button } from '../components/Button';
import { dateKey, dayLabel, shortTime, thousands, titleCase, weekdayShort } from '../lib/format';
import { useTheme } from '../theme/ThemeProvider';

interface DayBucket {
  key: string;
  date: Date;
  total: number;
}

interface DayGroup {
  key: string;
  total: number;
  entries: MealLog[];
}

function buildWeek(logs: MealLog[], today: Date): DayBucket[] {
  const days: DayBucket[] = [];
  for (let i = 6; i >= 0; i -= 1) {
    const date = new Date(today);
    date.setDate(today.getDate() - i);
    days.push({ key: dateKey(date), date, total: 0 });
  }
  const byKey = new Map(days.map((d) => [d.key, d]));
  for (const log of logs) {
    const bucket = byKey.get(dateKey(new Date(log.logged_at)));
    if (bucket) bucket.total += log.kcal;
  }
  return days;
}

function groupByDay(logs: MealLog[]): DayGroup[] {
  const groups = new Map<string, DayGroup>();
  for (const log of logs) {
    const key = dateKey(new Date(log.logged_at));
    const group = groups.get(key) ?? { key, total: 0, entries: [] };
    group.total += log.kcal;
    group.entries.push(log);
    groups.set(key, group);
  }
  return [...groups.values()].sort((a, b) => (a.key < b.key ? 1 : -1));
}

export function HistoryScreen() {
  const { colors, spacing, radii, shadows } = useTheme();
  const { accessToken, status } = useAuth();
  const [logs, setLogs] = useState<MealLog[]>([]);
  const [goal, setGoal] = useState(2000);
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
      const [allLogs, summary] = await Promise.all([
        fetchLogs(accessToken),
        fetchSummary(accessToken),
      ]);
      setLogs(allLogs);
      setGoal(summary.goal);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load your history.');
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  const remove = async (id: number) => {
    if (!accessToken) return;
    setLogs((prev) => prev.filter((l) => l.id !== id)); // optimistic
    try {
      await deleteLog(id, accessToken);
    } catch {
      void load(); // put it back if the delete didn't take
    }
  };

  if (status === 'guest') {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
        <View style={{ flex: 1, padding: spacing.xl, justifyContent: 'center', gap: spacing.m }}>
          <AppText variant="h2" tone="heading">
            No history yet
          </AppText>
          <AppText variant="body" tone="body">
            Sign in to keep a history of everything you log.
          </AppText>
        </View>
      </SafeAreaView>
    );
  }

  const today = new Date();
  const week = buildWeek(logs, today);
  const groups = groupByDay(logs);
  const maxBar = Math.max(goal, ...week.map((d) => d.total), 1);
  const activeDays = week.filter((d) => d.total > 0);
  const avg = activeDays.length
    ? Math.round(activeDays.reduce((sum, d) => sum + d.total, 0) / activeDays.length)
    : 0;
  const todayKey = dateKey(today);

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }} edges={['top']}>
      <ScrollView
        contentContainerStyle={{ padding: spacing.xl, gap: spacing.l }}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={() => void load()} tintColor={colors.sage} />}
      >
        <AppText variant="h1" tone="heading">
          History
        </AppText>

        {error ? (
          <View style={{ gap: spacing.s }}>
            <AppText variant="body" tone="body">
              {error}
            </AppText>
            <Button label="Retry" variant="secondary" onPress={() => void load()} />
          </View>
        ) : null}

        {/* weekly chart */}
        <View style={[{ backgroundColor: colors.card, borderRadius: radii.card, padding: spacing.l, gap: spacing.m }, shadows.light]}>
          <View style={{ flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between' }}>
            <AppText variant="subtitle" tone="heading">
              This week
            </AppText>
            <AppText variant="secondary" tone="caption">
              avg {thousands(avg)} kcal / day
            </AppText>
          </View>
          <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', height: 108 }}>
            {week.map((day) => {
              const over = day.total > goal;
              const barHeight = Math.round((day.total / maxBar) * 88);
              const isToday = day.key === todayKey;
              return (
                <View key={day.key} style={{ alignItems: 'center', gap: spacing.xs, flex: 1 }}>
                  <View
                    style={{
                      width: 22,
                      height: Math.max(4, barHeight),
                      borderRadius: 6,
                      backgroundColor: day.total === 0 ? colors.cardMuted : over ? colors.accent : colors.sage,
                    }}
                  />
                  <AppText variant="caption" tone={isToday ? 'heading' : 'caption'}>
                    {weekdayShort(day.date)}
                  </AppText>
                </View>
              );
            })}
          </View>
          <View style={{ flexDirection: 'row', gap: spacing.l }}>
            <Legend color={colors.sage} label="within goal" />
            <Legend color={colors.accent} label="over goal" />
          </View>
        </View>

        {/* day-grouped list */}
        {loading && logs.length === 0 ? (
          <ActivityIndicator color={colors.sage} style={{ marginVertical: spacing.l }} />
        ) : groups.length === 0 ? (
          <AppText variant="body" tone="body">
            No meals logged yet.
          </AppText>
        ) : (
          groups.map((group) => (
            <View key={group.key} style={{ gap: spacing.s }}>
              <AppText variant="caption" tone="caption">
                {dayLabel(group.key, today).toUpperCase()} · {thousands(group.total)} KCAL
              </AppText>
              {group.entries.map((entry) => (
                <View
                  key={entry.id}
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
                  <View style={{ flex: 1 }}>
                    <AppText variant="subtitle" tone="heading">
                      {titleCase(entry.label)}
                    </AppText>
                    <AppText variant="caption" tone="caption">
                      {shortTime(entry.logged_at)}
                    </AppText>
                  </View>
                  <View style={{ alignItems: 'flex-end' }}>
                    <AppText variant="subtitle" tone="heading">
                      {entry.kcal}
                    </AppText>
                    <AppText variant="caption" tone="sage">
                      kcal
                    </AppText>
                  </View>
                  <Pressable
                    onPress={() => void remove(entry.id)}
                    hitSlop={8}
                    accessibilityRole="button"
                    accessibilityLabel={`Delete ${titleCase(entry.label)}`}
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 16,
                      backgroundColor: colors.cardMuted,
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <Ionicons name="close" size={16} color={colors.caption} />
                  </Pressable>
                </View>
              ))}
            </View>
          ))
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  const { spacing } = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.xs }}>
      <View style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: color }} />
      <AppText variant="caption" tone="caption">
        {label}
      </AppText>
    </View>
  );
}
