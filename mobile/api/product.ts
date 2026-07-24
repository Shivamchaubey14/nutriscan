import { apiRequest } from './client';
import type { Nutrition, Portion } from './scan';

export interface Product {
  barcode: string;
  name: string;
  portion: Portion;
  nutrition: Nutrition;
}

/** FR-4: look up a scanned barcode in Open Food Facts (GET /api/v1/product/<barcode>/). */
export async function lookupProduct(barcode: string, token: string): Promise<Product> {
  return apiRequest<Product>(`/api/v1/product/${encodeURIComponent(barcode)}/`, { token });
}
