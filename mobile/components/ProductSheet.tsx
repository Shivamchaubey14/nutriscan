import { Ionicons } from '@expo/vector-icons';
import Slider from '@react-native-community/slider';
import { useState } from 'react';
import { ActivityIndicator, Pressable, View } from 'react-native';

import { ApiError } from '../api/client';
import { logMeal } from '../api/log';
import type { Product } from '../api/product';
import { thousands } from '../lib/format';
import { useTheme } from '../theme/ThemeProvider';
import { AppText } from './AppText';
import { Button } from './Button';

const MEALS = ['Breakfast', 'Lunch', 'Dinner', 'Snack'] as const;
type Meal = (typeof MEALS)[number];

interface Props {
  status: 'done' | 'failed';
  product: Product | null;
  error: string | null;
  token: string | null;
  onDismiss: () => void;
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

export function ProductSheet({ status, product, error, token, onDismiss }: Props) {
  const { colors, spacing, radii, shadows } = useTheme();
  const base = product?.portion.grams ?? 100;
  const [grams, setGrams] = useState(base);
  const [meal, setMeal] = useState<Meal>('Snack');
  const [logging, setLogging] = useState(false);
  const [logged, setLogged] = useState(false);
  const [logError, setLogError] = useState<string | null>(null);

  const sheet = (children: React.ReactNode) => (
    <View style={{ position: 'absolute', left: 0, right: 0, bottom: 0 }}>
      <View
        style={[
          {
            backgroundColor: colors.card,
            borderTopLeftRadius: radii.sheet,
            borderTopRightRadius: radii.sheet,
            paddingTop: spacing.m,
            paddingBottom: spacing.xl,
            paddingHorizontal: spacing.xl,
            gap: spacing.m,
          },
          shadows.large,
        ]}
      >
        <View
          style={{ width: 36, height: 4, borderRadius: 2, backgroundColor: colors.border, alignSelf: 'center' }}
        />
        {children}
      </View>
    </View>
  );

  if (status === 'failed') {
    return sheet(
      <>
        <AppText variant="title" tone="heading">
          No match
        </AppText>
        <AppText variant="body" tone="body">
          {error ?? 'Could not look up that barcode.'}
        </AppText>
        <Button label="Try again" onPress={onDismiss} />
      </>
    );
  }

  if (logged) {
    return sheet(
      <>
        <View style={{ alignItems: 'center', gap: spacing.s, paddingVertical: spacing.s }}>
          <Ionicons name="checkmark-circle" size={44} color={colors.sage} />
          <AppText variant="title" tone="heading">
            Logged to {meal}
          </AppText>
        </View>
        <Button label="Scan another" onPress={onDismiss} />
      </>
    );
  }

  if (!product) return null; // 'done' always carries a product; this narrows the type

  const ratio = grams / base;
  const kcalMin = Math.round(product.nutrition.kcal.min * ratio);
  const kcalMax = Math.round(product.nutrition.kcal.max * ratio);
  const min = Math.max(5, Math.round((base * 0.5) / 5) * 5);
  const max = Math.round((base * 4) / 5) * 5;

  const log = async () => {
    if (!token) return;
    setLogging(true);
    setLogError(null);
    try {
      await logMeal(
        {
          label: product.name.slice(0, 64),
          kcal: Math.round((kcalMin + kcalMax) / 2),
          portion_grams: grams,
          protein_g: round1(product.nutrition.protein_g * ratio),
          carbs_g: round1(product.nutrition.carbs_g * ratio),
          fat_g: round1(product.nutrition.fat_g * ratio),
          scan: null,
        },
        token
      );
      setLogged(true);
    } catch (err) {
      setLogError(err instanceof ApiError ? err.message : "Couldn't save to your log.");
    } finally {
      setLogging(false);
    }
  };

  return sheet(
    <>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.xs }}>
          <Ionicons name="barcode-outline" size={16} color={colors.caption} />
          <AppText variant="caption" tone="caption">
            PACKAGED · {product.barcode}
          </AppText>
        </View>
        <Pressable onPress={onDismiss} hitSlop={10}>
          <Ionicons name="close" size={22} color={colors.caption} />
        </Pressable>
      </View>

      <AppText variant="title" tone="heading">
        {product.name}
      </AppText>

      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ flexDirection: 'row', alignItems: 'baseline' }}>
          <AppText variant="h1" tone="heading">
            {kcalMin}–{kcalMax}
          </AppText>
          <AppText variant="subtitle" tone="sage">
            {' '}
            kcal
          </AppText>
        </View>
        <View
          style={{
            backgroundColor: colors.accentSoft,
            borderRadius: radii.chip,
            paddingVertical: spacing.xs,
            paddingHorizontal: spacing.s,
          }}
        >
          <AppText variant="caption" style={{ color: colors.onAccent }}>
            {product.nutrition.source}
          </AppText>
        </View>
      </View>

      <AppText variant="secondary" tone="body">
        P {round1(product.nutrition.protein_g * ratio)}g · C {round1(product.nutrition.carbs_g * ratio)}g · F{' '}
        {round1(product.nutrition.fat_g * ratio)}g
      </AppText>

      <View style={{ height: 1, backgroundColor: colors.border, marginVertical: spacing.xs }} />

      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <AppText variant="secondary" tone="caption">
          Portion
        </AppText>
        <AppText variant="secondary" tone="heading">
          {grams} g
        </AppText>
      </View>
      <Slider
        minimumValue={min}
        maximumValue={max}
        step={5}
        value={grams}
        onValueChange={(v) => setGrams(Math.round(v))}
        minimumTrackTintColor={colors.sage}
        maximumTrackTintColor={colors.border}
        thumbTintColor={colors.sage}
        style={{ width: '100%', height: 36 }}
      />

      {logError ? (
        <AppText variant="secondary" tone="error">
          {logError}
        </AppText>
      ) : null}

      <View style={{ flexDirection: 'row', gap: spacing.s }}>
        {MEALS.map((m) => {
          const active = m === meal;
          return (
            <Pressable
              key={m}
              onPress={() => setMeal(m)}
              style={{
                flex: 1,
                alignItems: 'center',
                backgroundColor: active ? colors.primary : colors.cardMuted,
                borderRadius: radii.chip,
                paddingVertical: spacing.s,
              }}
            >
              <AppText variant="caption" style={{ color: active ? colors.onPrimary : colors.body }}>
                {m}
              </AppText>
            </Pressable>
          );
        })}
      </View>

      <Button
        label={logging ? 'Logging…' : `Log to ${meal}`}
        variant="success"
        disabled={logging}
        onPress={() => void log()}
      />
      {logging ? <ActivityIndicator color={colors.sage} /> : null}
    </>
  );
}
