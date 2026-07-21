/** Storybook-style screen: every token and component in the current theme. */
import { ScrollView, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';

import { AppText } from '../components/AppText';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Chip } from '../components/Chip';
import { useTheme, useThemeToggle } from '../theme/ThemeProvider';
import { spacing, type Palette, type TypographyVariant } from '../theme/tokens';

const TYPE_SAMPLES: { variant: TypographyVariant; label: string }[] = [
  { variant: 'display', label: 'Display' },
  { variant: 'h1', label: 'Heading 1' },
  { variant: 'h2', label: 'Heading 2' },
  { variant: 'h3', label: 'Heading 3' },
  { variant: 'title', label: 'Title' },
  { variant: 'subtitle', label: 'Subtitle' },
  { variant: 'body', label: 'Body text' },
  { variant: 'secondary', label: 'Secondary text' },
  { variant: 'caption', label: 'CAPTION' },
];

const SWATCHES: (keyof Palette)[] = [
  'primary',
  'primaryMuted',
  'accent',
  'success',
  'warning',
  'error',
  'olive',
  'background',
  'card',
  'border',
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={{ gap: spacing.m }}>
      <AppText variant="h3" tone="heading">
        {title}
      </AppText>
      {children}
    </View>
  );
}

export function DesignSystemScreen() {
  const theme = useTheme();
  const toggle = useThemeToggle();
  const { colors } = theme;

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}>
      <StatusBar style={theme.isDark ? 'light' : 'dark'} />
      <ScrollView
        contentContainerStyle={{ padding: spacing.xl, gap: spacing.section }}
        showsVerticalScrollIndicator={false}
      >
        <View style={{ gap: spacing.xs }}>
          <AppText variant="display" tone="heading">
            NutriScan
          </AppText>
          <AppText variant="subtitle" tone="body">
            Design system · {theme.isDark ? 'Dark' : 'Light'}
          </AppText>
          <View style={{ marginTop: spacing.m }}>
            <Button
              label={theme.isDark ? 'Switch to light' : 'Switch to dark'}
              variant="secondary"
              onPress={toggle}
            />
          </View>
        </View>

        <Section title="Typography">
          <Card>
            <View style={{ gap: spacing.s }}>
              {TYPE_SAMPLES.map((sample) => (
                <AppText key={sample.variant} variant={sample.variant} tone="heading">
                  {sample.label}
                </AppText>
              ))}
            </View>
          </Card>
        </Section>

        <Section title="Colors">
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.m }}>
            {SWATCHES.map((name) => (
              <View key={name} style={{ alignItems: 'center', gap: spacing.xs, width: 72 }}>
                <View
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: theme.radii.card,
                    backgroundColor: colors[name],
                    borderWidth: 1,
                    borderColor: colors.border,
                  }}
                />
                <AppText variant="caption" tone="caption">
                  {name}
                </AppText>
              </View>
            ))}
          </View>
        </Section>

        <Section title="Buttons">
          <View style={{ gap: spacing.m }}>
            <Button label="Log to Breakfast" variant="primary" />
            <Button label="Scan again" variant="secondary" />
            <Button label="Within your goal" variant="success" />
            <Button label="Disabled" variant="primary" disabled />
          </View>
        </Section>

        <Section title="Confidence chips">
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.s }}>
            <Chip label="High" variant="high" />
            <Chip label="Medium" variant="medium" />
            <Chip label="Low" variant="low" />
            <Chip label="IFCT" variant="neutral" />
          </View>
        </Section>

        <Section title="Card">
          <Card>
            <View style={{ gap: spacing.s }}>
              <View
                style={{
                  flexDirection: 'row',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <AppText variant="title" tone="heading">
                  Samosa
                </AppText>
                <Chip label="High" variant="high" />
              </View>
              <AppText variant="h2" tone="primary">
                254–366 kcal
              </AppText>
              <AppText variant="secondary" tone="body">
                1 piece (100 g) · protein 5.1 g · carbs 33 g · fat 17.5 g
              </AppText>
            </View>
          </Card>
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}
