import { API_BASE_URL } from '../config';
import { ApiError } from './client';

export interface Portion {
  unit: string;
  grams: number;
  adjustable: boolean;
}

export interface Nutrition {
  kcal: { min: number; max: number };
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  source: string;
}

export interface ScanItem {
  label: string;
  confidence: number;
  portion: Portion;
  nutrition: Nutrition;
}

export interface Candidate {
  label: string;
  confidence: number;
}

export interface ScanResponse {
  scan_id: string;
  model_version: string;
  needs_confirmation: boolean;
  items: ScanItem[];
  candidates: Candidate[];
}

export async function scanImage(uri: string, token: string): Promise<ScanResponse> {
  const form = new FormData();
  // React Native FormData accepts a { uri, name, type } file part.
  form.append('image', { uri, name: 'scan.jpg', type: 'image/jpeg' } as unknown as Blob);

  const response = await fetch(`${API_BASE_URL}/api/v1/scan/`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const text = await response.text();
  const data: unknown = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail =
      data && typeof data === 'object' && typeof (data as { detail?: unknown }).detail === 'string'
        ? (data as { detail: string }).detail
        : `Scan failed (${response.status})`;
    throw new ApiError(response.status, detail);
  }
  return data as ScanResponse;
}
