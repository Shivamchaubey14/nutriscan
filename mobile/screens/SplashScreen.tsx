import { LinearGradient } from 'expo-linear-gradient';
import { Text, View } from 'react-native';

import { BrandMark } from '../components/BrandMark';

// The splash is a deliberate single-look brand moment (sage gradient, cream text),
// independent of the light/dark theme.
export function SplashScreen() {
  return (
    <LinearGradient
      colors={['#A9B898', '#8CA079', '#79896A']}
      style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: 22 }}
    >
      <BrandMark size={86} onDark />
      <View style={{ alignItems: 'center', gap: 6 }}>
        <Text style={{ fontSize: 34, fontWeight: '700', color: '#FBF9F1' }}>NutriScan</Text>
        <Text
          style={{
            fontSize: 13,
            fontWeight: '600',
            letterSpacing: 2,
            textTransform: 'uppercase',
            color: 'rgba(251, 249, 241, 0.85)',
          }}
        >
          Point · Scan · Know
        </Text>
      </View>
    </LinearGradient>
  );
}
