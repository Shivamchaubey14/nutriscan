import { Ionicons } from '@expo/vector-icons';
import { CameraView, useCameraPermissions, type BarcodeScanningResult } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import { useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '../api/client';
import { lookupProduct, type Product } from '../api/product';
import { scanImage, type ScanResponse } from '../api/scan';
import { useAuth } from '../auth/AuthProvider';
import { AppText } from '../components/AppText';
import { Button } from '../components/Button';
import { ProductSheet } from '../components/ProductSheet';
import { ScanResultSheet } from '../components/ScanResultSheet';
import { useTheme } from '../theme/ThemeProvider';

type Status = 'camera' | 'processing' | 'done' | 'failed';
type Mode = 'Food' | 'Barcode' | 'Label';

const GROUND = '#2C3327';
const OVERLAY = 'rgba(255,255,255,0.14)';

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
  const [mode, setMode] = useState<Mode>('Food');
  const [flash, setFlash] = useState(false);
  const [result, setResult] = useState<ScanResponse | null>(null);
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState<string | null>(null);
  // A single frame fires onBarcodeScanned repeatedly — latch so we look up once.
  const barcodeLatch = useRef(false);

  const reset = () => {
    setStatus('camera');
    setResult(null);
    setProduct(null);
    barcodeLatch.current = false;
  };

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

  const onBarcode = async ({ data }: BarcodeScanningResult) => {
    if (barcodeLatch.current || status !== 'camera' || !accessToken) return;
    barcodeLatch.current = true;
    setStatus('processing');
    setError(null);
    try {
      setProduct(await lookupProduct(data, accessToken));
      setStatus('done');
    } catch (err) {
      const msg = err instanceof ApiError && err.status === 404 ? "That product isn't in the database yet." : null;
      setError(msg ?? (err instanceof ApiError ? err.message : 'Could not look up that barcode.'));
      setStatus('failed');
    }
  };

  const selectMode = (next: Mode) => {
    if (next === 'Label') {
      Alert.alert('Coming soon', 'Scanning nutrition labels (OCR) is on the way.');
      return;
    }
    setMode(next);
    reset();
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
      <CameraView
        ref={cameraRef}
        style={{ flex: 1 }}
        facing="back"
        flash={flash ? 'on' : 'off'}
        barcodeScannerSettings={{ barcodeTypes: ['ean13', 'ean8', 'upc_a', 'upc_e', 'code128'] }}
        onBarcodeScanned={mode === 'Barcode' && status === 'camera' ? (e) => void onBarcode(e) : undefined}
      >
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
              {(['Food', 'Barcode', 'Label'] as Mode[]).map((m) => {
                const active = m === mode;
                return (
                  <Pressable
                    key={m}
                    onPress={() => selectMode(m)}
                    style={{
                      borderRadius: 17,
                      paddingHorizontal: 14,
                      paddingVertical: 6,
                      backgroundColor: active ? '#FBF9F1' : 'transparent',
                    }}
                  >
                    <AppText variant="caption" style={{ color: active ? GROUND : '#FBF9F1' }}>
                      {m}
                    </AppText>
                  </Pressable>
                );
              })}
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
                  {mode === 'Barcode' ? 'Looking up product…' : 'Identifying your food…'}
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
            {mode === 'Barcode' ? (
              <View
                style={{
                  backgroundColor: 'rgba(0,0,0,0.45)',
                  borderRadius: 16,
                  paddingHorizontal: spacing.l,
                  paddingVertical: spacing.m,
                }}
              >
                <AppText variant="secondary" style={{ color: '#FBF9F1' }}>
                  Point at a barcode
                </AppText>
              </View>
            ) : (
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
            )}
            <View style={{ width: 46 }} />
          </View>
        </SafeAreaView>
      </CameraView>

      {(status === 'done' || status === 'failed') &&
        (mode === 'Barcode' ? (
          <ProductSheet
            status={status}
            product={product}
            error={error}
            token={accessToken}
            onDismiss={reset}
          />
        ) : (
          <ScanResultSheet
            status={status}
            result={result}
            error={error}
            token={accessToken}
            onDismiss={reset}
          />
        ))}
    </View>
  );
}
