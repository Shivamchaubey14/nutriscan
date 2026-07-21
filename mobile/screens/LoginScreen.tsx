import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import { AppText } from '../components/AppText';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { useTheme } from '../theme/ThemeProvider';
import type { AuthScreenProps } from '../navigation/types';

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
        <ScrollView contentContainerStyle={{ padding: spacing.xl, gap: spacing.xl, flexGrow: 1, justifyContent: 'center' }}>
          <View style={{ gap: spacing.xs }}>
            <AppText variant="display" tone="heading">
              Welcome back
            </AppText>
            <AppText variant="body" tone="body">
              Sign in to scan meals and track your day.
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
            <Button label="Continue as guest" variant="secondary" onPress={continueAsGuest} />
          </View>

          <Pressable onPress={() => navigation.navigate('Register')} style={{ alignSelf: 'center' }}>
            <AppText variant="secondary" tone="primary">
              New here? Create an account
            </AppText>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
