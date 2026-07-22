import { Ionicons } from '@expo/vector-icons';
import {
  createBottomTabNavigator,
  type BottomTabBarButtonProps,
} from '@react-navigation/bottom-tabs';
import { Pressable, View } from 'react-native';

import { HistoryScreen } from '../screens/HistoryScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { PlanScreen } from '../screens/Placeholder';
import { ProfileScreen } from '../screens/ProfileScreen';
import { ScanScreen } from '../screens/ScanScreen';
import { useTheme } from '../theme/ThemeProvider';
import type { MainTabParamList } from './types';

const Tab = createBottomTabNavigator<MainTabParamList>();

const ICONS: Record<keyof MainTabParamList, keyof typeof Ionicons.glyphMap> = {
  Home: 'home-outline',
  History: 'time-outline',
  Scan: 'add',
  Plan: 'restaurant-outline',
  Profile: 'person-outline',
};

function ScanFab({ onPress, accessibilityState }: BottomTabBarButtonProps) {
  const { colors, shadows } = useTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={accessibilityState}
      onPress={onPress}
      style={{ top: -18, justifyContent: 'center', alignItems: 'center' }}
    >
      <View
        style={[
          {
            width: 58,
            height: 58,
            borderRadius: 29,
            backgroundColor: colors.sage,
            justifyContent: 'center',
            alignItems: 'center',
          },
          shadows.medium,
        ]}
      >
        <Ionicons name="scan-outline" size={28} color={colors.onSage} />
      </View>
    </Pressable>
  );
}

export function MainTabs() {
  const { colors } = useTheme();
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.caption,
        tabBarStyle: {
          backgroundColor: colors.card,
          borderTopColor: colors.border,
        },
        tabBarIcon: ({ color, size }) => (
          <Ionicons name={ICONS[route.name]} size={size} color={color} />
        ),
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="History" component={HistoryScreen} />
      <Tab.Screen
        name="Scan"
        component={ScanScreen}
        options={{ tabBarLabel: () => null, tabBarButton: (props) => <ScanFab {...props} /> }}
      />
      <Tab.Screen name="Plan" component={PlanScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}
