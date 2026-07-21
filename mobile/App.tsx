import { SafeAreaProvider } from 'react-native-safe-area-context';

import { DesignSystemScreen } from './screens/DesignSystemScreen';
import { ThemeProvider } from './theme/ThemeProvider';

export default function App() {
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <DesignSystemScreen />
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
