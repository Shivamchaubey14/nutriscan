import { useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import { AppText } from '../components/AppText';
import { BrandMark } from '../components/BrandMark';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { useTheme } from '../theme/ThemeProvider';
import type { AuthScreenProps } from '../navigation/types';

function Divider({ label }: { label: string }) {
  const { colors, spacing, typography } = useTheme();
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: spacing.m }}>
      <View style={{ flex: 1, height: 1, backgroundColor: colors.border }} />
      <Text style={[typography.caption, { color: colors.caption }]}>{label}</Text>
      <View style={{ flex: 1, height: 1, backgroundColor: colors.border }} />
    </View>
  );
}

function SocialButton({ label, color }: { label: string; color: string }) {
  const { colors, radii, spacing, typography } = useTheme();
  return (
    <Pressable
      onPress={() => Alert.alert('Coming soon', `${label} sign-in isn't wired up yet.`)}
      style={{
        flex: 1,
        alignItems: 'center',
        backgroundColor: colors.card,
        borderWidth: 1,
        borderColor: colors.border,
        borderRadius: radii.button,
        paddingVertical: spacing.m,
      }}
    >
      <Text style={[typography.button, { color }]}>{label}</Text>
    </Pressable>
  );
}

export function LoginScreen({ navigation }: AuthScreenProps<'Login'>) {
  const { login, continueAsGuest } = useAuth();
  const { colors, spacing } = useTheme();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async () => {
    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in. Check your connection.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView contentContainerStyle={{ padding: spacing.xl, gap: spacing.xl }}>
          <BrandMark size={52} />

          <View style={{ gap: spacing.xs }}>
            <AppText variant="display" tone="heading">
              Welcome to{'\n'}NutriScan
            </AppText>
            <AppText variant="body" tone="body">
              Scan your plate, get calories in seconds. Sign in to keep your history and goals.
            </AppText>
          </View>

          <View style={{ gap: spacing.l }}>
            <Input
              label="Email"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              keyboardType="email-address"
              autoComplete="email"
              placeholder="you@example.com"
            />
            <Input
              label="Password"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              placeholder="••••••••"
              error={error}
            />
            <Button label={busy ? 'Signing in…' : 'Sign in'} onPress={onSubmit} disabled={busy} />
          </View>

          <Divider label="or continue with" />
          <View style={{ flexDirection: 'row', gap: spacing.m }}>
            <SocialButton label="Google" color="#C87A45" />
            <SocialButton label="Apple" color="#4A6DA7" />
          </View>

          <View style={{ alignItems: 'center', gap: spacing.xs, marginTop: spacing.s }}>
            <Pressable onPress={continueAsGuest}>
              <AppText variant="subtitle" tone="heading">
                Continue as guest
              </AppText>
            </Pressable>
            <AppText variant="caption" tone="caption" style={{ textAlign: 'center' }}>
              Guest history stays on this device. Create an account anytime to keep it.
            </AppText>
            <Pressable onPress={() => navigation.navigate('Register')} style={{ marginTop: spacing.s }}>
              <AppText variant="secondary" tone="primary">
                New here? Create an account
              </AppText>
            </Pressable>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
