import {
  DarkTheme,
  DefaultTheme,
  NavigationContainer,
  type Theme as NavTheme,
} from '@react-navigation/native';

import { useAuth } from '../auth/AuthProvider';
import { SplashScreen } from '../screens/SplashScreen';
import { useTheme } from '../theme/ThemeProvider';
import { AuthStack } from './AuthStack';
import { MainTabs } from './MainTabs';

export function RootNavigator() {
  const { status } = useAuth();
  const { colors, isDark } = useTheme();

  const navTheme: NavTheme = {
    ...(isDark ? DarkTheme : DefaultTheme),
    colors: {
      ...(isDark ? DarkTheme : DefaultTheme).colors,
      background: colors.background,
      card: colors.card,
      text: colors.heading,
      border: colors.border,
      primary: colors.primary,
    },
  };

  if (status === 'loading') {
    return <SplashScreen />;
  }

  const signedIn = status === 'authenticated' || status === 'guest';
  return (
    <NavigationContainer theme={navTheme}>
      {signedIn ? <MainTabs /> : <AuthStack />}
    </NavigationContainer>
  );
}
