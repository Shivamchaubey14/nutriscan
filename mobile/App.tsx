import { SafeAreaProvider } from 'react-native-safe-area-context';

import { AuthProvider } from './auth/AuthProvider';
import { RootNavigator } from './navigation/RootNavigator';
import { ThemeProvider } from './theme/ThemeProvider';

export default function App() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <AuthProvider>
          <RootNavigator />
        </AuthProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
