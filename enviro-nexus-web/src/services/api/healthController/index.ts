import { requestJson } from "../client";

/** GET /api/v1/health — 健康检查 */
export function healthCheck(options?: { signal?: AbortSignal }) {
  return requestJson<Health.HealthData>("/health", {
    method: "GET",
    signal: options?.signal,
  });
}

export type HealthData = Health.HealthData;
