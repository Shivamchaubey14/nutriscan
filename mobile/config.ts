/**
 * API base URL.
 *
 * In dev the backend runs on your machine (docker compose) and the phone reaches
 * it over the LAN — never `localhost`, which on the phone means the phone itself.
 * We derive the machine's LAN IP from Expo's Metro host and target port 8000.
 * Override by setting `expo.extra.apiUrl` in app.json (e.g. a staging URL).
 */
import Constants from 'expo-constants';

const BACKEND_PORT = 8000;

function resolveApiBaseUrl(): string {
  const configured = (Constants.expoConfig?.extra as { apiUrl?: string } | undefined)?.apiUrl;
  if (configured) return configured;

  // hostUri looks like "192.168.1.20:8081" — the dev machine's LAN address.
  const hostUri = Constants.expoConfig?.hostUri;
  const host = hostUri?.split(':')[0];
  if (host) return `http://${host}:${BACKEND_PORT}`;

  return `http://localhost:${BACKEND_PORT}`;
}

export const API_BASE_URL = resolveApiBaseUrl();
