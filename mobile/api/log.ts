import { apiRequest } from './client';

export interface LogEntry {
  label: string;
  kcal: number;
  portion_grams: number;
  scan: string | null;
}

export interface MealLog extends LogEntry {
  id: number;
  logged_at: string;
}

/** Record an eaten item against the user's daily total (POST /api/v1/log/). */
export async function logMeal(entry: LogEntry, token: string): Promise<MealLog> {
  return apiRequest<MealLog>('/api/v1/log/', { method: 'POST', body: entry, token });
}
