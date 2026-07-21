import { Ionicons } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '../api/client';
import { scanImage, type ScanResponse } from '../api/scan';
import { useAuth } from '../auth/AuthProvider';
import { AppText } from '../components/AppText';
import { Button } from '../components/Button';
import { Chip } from '../components/Chip';
import { useTheme } from '../theme/ThemeProvider';

type Status = 'camera' | 'processing' | 'done' | 'failed';

const GROUND = '#2C3327';
const OVERLAY = 'rgba(255,255,255,0.14)';

function confidenceChip(confidence: number): { label: string; variant: 'high' | 'medium' | 'low' } {
  const pct = Math.round(confidence * 100);
  if (confidence >= 0.75) return { label: `High · ${pct}%`, variant: 'high' };
  if (confidence >= 0.55) return { label: `Medium · ${pct}%`, variant: 'medium' };
  return { label: `Low · ${pct}%`, variant: 'low' };
}

function Corners() {
  const size = 34;
  const corner = (pos: object) => (
    <View
      style={{
        position: 'absolute',
        width: size,
        height: size,
        borderColor: 'rgba(255,255,255,0.85)',
        ...pos,
      }}
    />
  );
  return (
    <View pointerEvents="none" style={{ position: 'absolute', inset: 40 }}>
      {corner({ top: 0, left: 0, borderTopWidth: 3, borderLeftWidth: 3, borderTopLeftRadius: 10 })}
      {corner({ top: 0, right: 0, borderTopWidth: 3, borderRightWidth: 3, borderTopRightRadius: 10 })}
      {corner({ bottom: 0, left: 0, borderBottomWidth: 3, borderLeftWidth: 3, borderBottomLeftRadius: 10 })}
      {corner({ bottom: 0, right: 0, borderBottomWidth: 3, borderRightWidth: 3, borderBottomRightRadius: 10 })}
    </View>
  );
}

function RoundBtn({ name, onPress }: { name: keyof typeof Ionicons.glyphMap; onPress?: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      style={{
        width: 46,
        height: 46,
        borderRadius: 23,
        backgroundColor: OVERLAY,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Ionicons name={name} size={22} color="#FBF9F1" />
    </Pressable>
  );
}

export function ScanScreen() {
  const { accessToken, status: authStatus, logout } = useAuth();
  const { colors, spacing } = useTheme();
  const [permission, requestPermission] = useCameraPermissions();
  const cameraRef = useRef<CameraView>(null);
  const [status, setStatus] = useState<Status>('camera');
  const [flash, setFlash] = useState(false);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const upload = async (uri: string) => {
    if (!accessToken) return;
    setStatus('processing');
    setError(null);
    try {
      setResult(await scanImage(uri, accessToken));
      setStatus('done');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reach the scanner.');
      setStatus('failed');
    }
  };

  const capture = async () => {
    const photo = await cameraRef.current?.takePictureAsync({ quality: 0.6 });
    if (photo?.uri) void upload(photo.uri);
  };

  const pickFromGallery = async () => {
    const picked = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 0.6 });
    if (!picked.canceled && picked.assets[0]) void upload(picked.assets[0].uri);
  };

  // Guests can't scan (the endpoint needs a signed-in user).
  if (authStatus === 'guest') {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
        <View style={{ flex: 1, padding: spacing.xl, justifyContent: 'center', gap: spacing.m }}>
          <AppText variant="h2" tone="heading">
            Sign in to scan
          </AppText>
          <AppText variant="body" tone="body">
            Scanning saves results to your history, so it needs an account.
          </AppText>
          <Button label="Sign in" onPress={() => void logout()} />
        </View>
      </SafeAreaView>
    );
  }

  if (!permission) {
    return <View style={{ flex: 1, backgroundColor: GROUND }} />;
  }

  if (!permission.granted) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
        <View style={{ flex: 1, padding: spacing.xl, justifyContent: 'center', gap: spacing.m }}>
          <AppText variant="h2" tone="heading">
            Camera access
          </AppText>
          <AppText variant="body" tone="body">
            NutriScan needs your camera to identify meals. Photos are used only for this scan.
          </AppText>
          <Button label="Allow camera" onPress={() => void requestPermission()} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: GROUND }}>
      <CameraView ref={cameraRef} style={{ flex: 1 }} facing="back" flash={flash ? 'on' : 'off'}>
        <SafeAreaView style={{ flex: 1 }} edges={['top', 'bottom']}>
          {/* top controls */}
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingHorizontal: spacing.l,
              paddingTop: spacing.s,
            }}
          >
            <RoundBtn name="close" />
            <View style={{ flexDirection: 'row', backgroundColor: OVERLAY, borderRadius: 20, padding: 3 }}>
              {['Food', 'Barcode', 'Label'].map((mode, i) => (
                <View
                  key={mode}
                  style={{
                    borderRadius: 17,
                    paddingHorizontal: 14,
                    paddingVertical: 6,
                    backgroundColor: i === 0 ? '#FBF9F1' : 'transparent',
                  }}
                >
                  <AppText variant="caption" style={{ color: i === 0 ? GROUND : '#FBF9F1' }}>
                    {mode}
                  </AppText>
                </View>
              ))}
            </View>
            <RoundBtn name={flash ? 'flash' : 'flash-off'} onPress={() => setFlash((f) => !f)} />
          </View>

          {status === 'processing' ? (
            <View style={{ alignItems: 'center', marginTop: spacing.l }}>
              <View
                style={{
                  flexDirection: 'row',
                  alignItems: 'center',
                  gap: spacing.s,
                  backgroundColor: 'rgba(0,0,0,0.45)',
                  borderRadius: 16,
                  paddingHorizontal: spacing.l,
                  paddingVertical: spacing.s,
                }}
              >
                <ActivityIndicator color="#FBF9F1" size="small" />
                <AppText variant="secondary" style={{ color: '#FBF9F1' }}>
                  Identifying your food…
                </AppText>
              </View>
            </View>
          ) : null}

          <Corners />
          <View style={{ flex: 1 }} />

          {/* bottom controls */}
          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingHorizontal: spacing.xl,
              paddingBottom: spacing.s,
            }}
          >
            <RoundBtn name="images-outline" onPress={() => void pickFromGallery()} />
            <Pressable
              onPress={() => void capture()}
              disabled={status === 'processing'}
              style={{
                width: 76,
                height: 76,
                borderRadius: 38,
                backgroundColor: colors.sage,
                borderWidth: 4,
                borderColor: 'rgba(255,255,255,0.6)',
                opacity: status === 'processing' ? 0.6 : 1,
              }}
            />
            <View style={{ width: 46 }} />
          </View>
        </SafeAreaView>
      </CameraView>

      {(status === 'done' || status === 'failed') && (
        <ResultSheet
          status={status}
          result={result}
          error={error}
          onDismiss={() => {
            setStatus('camera');
            setResult(null);
          }}
        />
      )}
    </View>
  );
}

function ResultSheet({
  status,
  result,
  error,
  onDismiss,
}: {
  status: Status;
  result: ScanResponse | null;
  error: string | null;
  onDismiss: () => void;
}) {
  const { colors, spacing, radii, shadows } = useTheme();
  return (
    <View style={{ position: 'absolute', left: 0, right: 0, bottom: 0 }}>
      <View
        style={[
          {
            backgroundColor: colors.card,
            borderTopLeftRadius: radii.sheet,
            borderTopRightRadius: radii.sheet,
            padding: spacing.xl,
            gap: spacing.m,
          },
          shadows.large,
        ]}
      >
        <View style={{ width: 36, height: 4, borderRadius: 2, backgroundColor: colors.border, alignSelf: 'center' }} />

        {status === 'failed' ? (
          <>
            <AppText variant="title" tone="heading">
              Scan failed
            </AppText>
            <AppText variant="body" tone="body">
              {error ?? 'Something went wrong.'}
            </AppText>
            <Button label="Try again" onPress={onDismiss} />
          </>
        ) : (
          <ScrollView style={{ maxHeight: 360 }} contentContainerStyle={{ gap: spacing.m }}>
            <AppText variant="caption" tone="caption">
              {(result?.items.length ?? 0) > 0
                ? `DETECTED · ${result?.model_version}`
                : 'NO CONFIDENT MATCH'}
            </AppText>
            {result?.items.map((item) => {
              const chip = confidenceChip(item.confidence);
              return (
                <View key={item.label} style={{ gap: spacing.xs }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                    <AppText variant="title" tone="heading">
                      {item.label.replace(/_/g, ' ')}
                    </AppText>
                    <Chip label={chip.label} variant={chip.variant} />
                  </View>
                  <AppText variant="h2" tone="sage">
                    {item.nutrition.kcal.min}–{item.nutrition.kcal.max} kcal
                  </AppText>
                  <AppText variant="secondary" tone="body">
                    {item.portion.unit} · {item.portion.grams} g · P {item.nutrition.protein_g} · C{' '}
                    {item.nutrition.carbs_g} · F {item.nutrition.fat_g} · {item.nutrition.source}
                  </AppText>
                </View>
              );
            })}
            {result?.needs_confirmation ? (
              <AppText variant="secondary" tone="body">
                Not fully sure — you'll be able to pick from the top matches next.
              </AppText>
            ) : null}
            <Button label="Scan another" variant="secondary" onPress={onDismiss} />
          </ScrollView>
        )}
      </View>
    </View>
  );
}
