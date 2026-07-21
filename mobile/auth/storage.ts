/** Token storage: expo-secure-store on device, in-memory on web (where it's absent). */
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const memory: Record<string, string> = {};
const isWeb = Platform.OS === 'web';

export async function setItem(key: string, value: string): Promise<void> {
  if (isWeb) {
    memory[key] = value;
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

export async function getItem(key: string): Promise<string | null> {
  if (isWeb) return memory[key] ?? null;
  return SecureStore.getItemAsync(key);
}

export async function deleteItem(key: string): Promise<void> {
  if (isWeb) {
    delete memory[key];
    return;
  }
  await SecureStore.deleteItemAsync(key);
}
