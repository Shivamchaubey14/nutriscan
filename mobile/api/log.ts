import { apiRequest } from './client';

export interface LogEntry {
  label: string;
  kcal: number;
  portion_grams: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  scan: string | null;
}

export interface MealLog extends LogEntry {
  id: number;
  logged_at: string;
}

export interface DailySummary {
  date: string;
  total_kcal: number;
  goal: number;
  remaining: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  count: number;
}

/** Record an eaten item against the user's daily total (POST /api/v1/log/). */
export async function logMeal(entry: LogEntry, token: string): Promise<MealLog> {
  return apiRequest<MealLog>('/api/v1/log/', { method: 'POST', body: entry, token });
}

/** All logged meals, newest first; optionally filtered to one YYYY-MM-DD day. */
export async function fetchLogs(token: string, date?: string): Promise<MealLog[]> {
  const query = date ? `?date=${date}` : '';
  return apiRequest<MealLog[]>(`/api/v1/log/${query}`, { token });
}

/** Daily totals vs the user's calorie goal (GET /api/v1/log/summary/). */
export async function fetchSummary(token: string, date?: string): Promise<DailySummary> {
  const query = date ? `?date=${date}` : '';
  return apiRequest<DailySummary>(`/api/v1/log/summary/${query}`, { token });
}

/** Remove a logged meal (DELETE /api/v1/log/<id>/). */
export async function deleteLog(id: number, token: string): Promise<void> {
  await apiRequest(`/api/v1/log/${id}/`, { method: 'DELETE', token });
}
