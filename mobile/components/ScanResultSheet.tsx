import { Ionicons } from '@expo/vector-icons';
import Slider from '@react-native-community/slider';
import { useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, View } from 'react-native';

import { ApiError } from '../api/client';
import { logMeal } from '../api/log';
import { sendFeedback, type Candidate, type ScanItem, type ScanResponse } from '../api/scan';
import { titleCase } from '../lib/format';
import { useTheme } from '../theme/ThemeProvider';
import { AppText } from './AppText';
import { Button } from './Button';
import { Chip } from './Chip';

const MEALS = ['Breakfast', 'Lunch', 'Dinner', 'Snack'] as const;
type Meal = (typeof MEALS)[number];

interface Props {
  status: 'done' | 'failed';
  result: ScanResponse | null;
  error: string | null;
  token: string | null;
  onDismiss: () => void;
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

function formatCount(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function confidenceChip(confidence: number): { label: string; variant: 'high' | 'medium' | 'low' } {
  const pct = Math.round(confidence * 100);
  if (confidence >= 0.75) return { label: `High · ${pct}%`, variant: 'high' };
  if (confidence >= 0.55) return { label: `Medium · ${pct}%`, variant: 'medium' };
  return { label: `Low · ${pct}%`, variant: 'low' };
}

// Calories scale linearly with grams, so a client-side portion adjustment just
// rescales the server's default-portion numbers — no round trip per drag.
function scaleItem(item: ScanItem, grams: number) {
  const ratio = grams / item.portion.grams;
  const { kcal, protein_g, carbs_g, fat_g } = item.nutrition;
  return {
    kcalMin: Math.round(kcal.min * ratio),
    kcalMax: Math.round(kcal.max * ratio),
    protein: round1(protein_g * ratio),
    carbs: round1(carbs_g * ratio),
    fat: round1(fat_g * ratio),
    count: round1(ratio),
  };
}

export function ScanResultSheet({ status, result, error, token, onDismiss }: Props) {
  const { colors, spacing, radii, shadows } = useTheme();

  const lowConfidence = result?.needs_confirmation ?? false;
  const [picked, setPicked] = useState<ScanItem | null>(null);
  const [grams, setGrams] = useState<Record<string, number>>({});
  const [meal, setMeal] = useState<Meal>('Breakfast');
  const [logging, setLogging] = useState(false);
  const [logged, setLogged] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [noteIsError, setNoteIsError] = useState(false);

  const gramsFor = (item: ScanItem) => grams[item.label] ?? item.portion.grams;
  const setGramsFor = (label: string, value: number) =>
    setGrams((prev) => ({ ...prev, [label]: value }));

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

  // ---- failure ---------------------------------------------------------------
  if (status === 'failed') {
    return sheet(
      <>
        <AppText variant="title" tone="heading">
          Scan failed
        </AppText>
        <AppText variant="body" tone="body">
          {error ?? 'Something went wrong.'}
        </AppText>
        <Button label="Try again" onPress={onDismiss} />
      </>
    );
  }

  // ---- a note we recorded, nothing more to show ------------------------------
  if (note) {
    return sheet(
      <>
        <AppText variant="title" tone="heading">
          {noteIsError ? 'Something went wrong' : 'Thanks — noted'}
        </AppText>
        <AppText variant="body" tone="body">
          {note}
        </AppText>
        <Button label={noteIsError ? 'Try again' : 'Done'} onPress={onDismiss} />
      </>
    );
  }

  // ---- logged confirmation ---------------------------------------------------
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

  // ---- low-confidence: pick the right dish -----------------------------------
  if (lowConfidence && picked === null) {
    const originalLabel = result?.items[0]?.label ?? result?.candidates[0]?.label;
    const choose = (c: Candidate) => {
      const corrected = c.label !== originalLabel;
      if (token && result) {
        void sendFeedback(
          result.scan_id,
          { confirmed: !corrected, corrected_label: corrected ? c.label : '' },
          token
        ).catch(() => undefined);
      }
      if (c.nutrition && c.portion) {
        setPicked({
          label: c.label,
          confidence: c.confidence,
          portion: c.portion,
          nutrition: c.nutrition,
        });
      } else {
        setNoteIsError(false);
        setNote(`We've recorded that it's ${titleCase(c.label)}. Nutrition for it is coming soon.`);
      }
    };
    const searchManually = () => {
      if (token && result) {
        void sendFeedback(result.scan_id, { confirmed: false, corrected_label: '' }, token).catch(
          () => undefined
        );
      }
      onDismiss();
    };

    return sheet(
      <>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.xs }}>
          <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: colors.error }} />
          <AppText variant="caption" tone="caption">
            AWAITING CONFIRMATION
          </AppText>
        </View>
        <AppText variant="h2" tone="heading">
          Not quite sure — is this…
        </AppText>
        <AppText variant="secondary" tone="body">
          Confidence below 55%. Your pick improves the model.
        </AppText>
        <View style={{ gap: spacing.s, marginTop: spacing.xs }}>
          {result?.candidates.map((c, i) => {
            const pct = Math.round(c.confidence * 100);
            const top = i === 0;
            return (
              <Pressable
                key={c.label}
                onPress={() => choose(c)}
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: spacing.m,
                  backgroundColor: top ? colors.sageSoft : colors.card,
                  borderWidth: 1,
                  borderColor: top ? colors.sage : colors.border,
                  borderRadius: radii.card,
                  paddingVertical: spacing.m,
                  paddingHorizontal: spacing.l,
                }}
              >
                <AppText variant="subtitle" tone="heading" style={{ flex: 1 }}>
                  {titleCase(c.label)}
                </AppText>
                <View
                  style={{
                    width: 72,
                    height: 6,
                    borderRadius: 3,
                    backgroundColor: colors.border,
                    overflow: 'hidden',
                  }}
                >
                  <View
                    style={{
                      width: `${Math.max(4, pct)}%`,
                      height: '100%',
                      borderRadius: 3,
                      backgroundColor: colors.sage,
                    }}
                  />
                </View>
                <AppText variant="secondary" tone="body" style={{ width: 40, textAlign: 'right' }}>
                  {pct}%
                </AppText>
              </Pressable>
            );
          })}
        </View>
        <Pressable onPress={searchManually} style={{ alignSelf: 'center', paddingVertical: spacing.s }}>
          <AppText variant="secondary" tone="caption">
            None of these — search manually
          </AppText>
        </Pressable>
      </>
    );
  }

  // ---- the money screen: detected items with adjustable portions -------------
  const items = lowConfidence ? (picked ? [picked] : []) : (result?.items ?? []);

  if (items.length === 0) {
    // High-confidence guess with no nutrition mapping yet.
    const label = result?.candidates[0]?.label;
    return sheet(
      <>
        <AppText variant="title" tone="heading">
          {label ? titleCase(label) : 'No confident match'}
        </AppText>
        <AppText variant="body" tone="body">
          {label
            ? "We recognised this dish, but its nutrition isn't in the database yet."
            : "We couldn't identify the food. Try another angle or better light."}
        </AppText>
        <Button label="Scan another" onPress={onDismiss} />
      </>
    );
  }

  const scaled = items.map((item) => scaleItem(item, gramsFor(item)));
  const totalMin = scaled.reduce((sum, s) => sum + s.kcalMin, 0);
  const totalMax = scaled.reduce((sum, s) => sum + s.kcalMax, 0);

  const log = async () => {
    if (!token) return;
    setLogging(true);
    try {
      for (let i = 0; i < items.length; i += 1) {
        const item = items[i];
        const s = scaled[i];
        await logMeal(
          {
            label: item.label,
            kcal: Math.round((s.kcalMin + s.kcalMax) / 2),
            portion_grams: gramsFor(item),
            protein_g: s.protein,
            carbs_g: s.carbs,
            fat_g: s.fat,
            scan: result?.scan_id ?? null,
          },
          token
        );
      }
      setLogged(true);
    } catch (err) {
      setNoteIsError(true);
      setNote(err instanceof ApiError ? err.message : "Couldn't save to your log.");
    } finally {
      setLogging(false);
    }
  };

  return sheet(
    <>
      <View style={{ flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <View style={{ flex: 1, gap: 2 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.xs }}>
            <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: colors.sage }} />
            <AppText variant="caption" tone="caption">
              {items.length} ITEM{items.length === 1 ? '' : 'S'} DETECTED
            </AppText>
          </View>
          <AppText variant="caption" tone="caption">
            model {result?.model_version} · tap a value to adjust
          </AppText>
        </View>
        <Pressable onPress={onDismiss} hitSlop={10}>
          <Ionicons name="close" size={22} color={colors.caption} />
        </Pressable>
      </View>

      <ScrollView style={{ maxHeight: 320 }} contentContainerStyle={{ gap: spacing.m }}>
        {items.map((item, i) => {
          const g = gramsFor(item);
          const s = scaled[i];
          const chip = confidenceChip(item.confidence);
          const min = Math.max(5, Math.round((item.portion.grams * 0.33) / 5) * 5);
          const max = Math.round((item.portion.grams * 2.5) / 5) * 5;
          return (
            <View
              key={item.label}
              style={{
                borderWidth: 1,
                borderColor: colors.border,
                borderRadius: radii.card,
                padding: spacing.l,
                gap: spacing.s,
              }}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <AppText variant="title" tone="heading">
                  {titleCase(item.label)}
                </AppText>
                <Chip label={chip.label} variant={chip.variant} />
              </View>

              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <View style={{ flexDirection: 'row', alignItems: 'baseline' }}>
                  <AppText variant="h1" tone="heading">
                    {s.kcalMin}–{s.kcalMax}
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
                    {item.nutrition.source}
                  </AppText>
                </View>
              </View>

              <AppText variant="secondary" tone="body">
                P {s.protein}g · C {s.carbs}g · F {s.fat}g
              </AppText>

              <View style={{ height: 1, backgroundColor: colors.border, marginVertical: spacing.xs }} />

              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <AppText variant="secondary" tone="caption">
                  Portion
                </AppText>
                <AppText variant="secondary" tone="heading">
                  {formatCount(s.count)} {item.portion.unit} · {g} g
                </AppText>
              </View>
              <Slider
                minimumValue={min}
                maximumValue={max}
                step={5}
                value={g}
                onValueChange={(v) => setGramsFor(item.label, Math.round(v))}
                minimumTrackTintColor={colors.sage}
                maximumTrackTintColor={colors.border}
                thumbTintColor={colors.sage}
                style={{ width: '100%', height: 36 }}
              />
              <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                <AppText variant="caption" tone="caption">
                  {min} g
                </AppText>
                <AppText variant="caption" tone="caption">
                  {max} g
                </AppText>
              </View>
            </View>
          );
        })}
      </ScrollView>

      {/* meal picker */}
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

      {/* total + log */}
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.m }}>
        <View>
          <AppText variant="title" tone="heading">
            {totalMin}–{totalMax}
          </AppText>
          <AppText variant="caption" tone="caption">
            total kcal
          </AppText>
        </View>
        <View style={{ flex: 1 }}>
          <Button
            label={logging ? 'Logging…' : `Log to ${meal}`}
            variant="success"
            disabled={logging}
            onPress={() => void log()}
          />
        </View>
      </View>
      {logging ? <ActivityIndicator color={colors.sage} /> : null}
    </>
  );
}
