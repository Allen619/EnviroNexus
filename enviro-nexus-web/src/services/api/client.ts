/**
 * API 请求基础设施（各模块共用）
 */

/** 开发默认走 Vite 代理（同源 /api）；生产可设 VITE_API_BASE_URL */
const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ??
  "";

const API_PREFIX = "/api/v1";

export type ApiClientOptions = {
  /** POC 用户标识，会话与因子查询必填 */
  userId: string;
  signal?: AbortSignal;
};

export class ApiError extends Error {
  readonly status: number;
  readonly body: API.ErrorResponse;

  constructor(status: number, body: API.ErrorResponse) {
    super(body.message || `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export function buildUrl(
  path: string,
  query?: Record<string, string | number | undefined>
) {
  const pathWithPrefix = `${API_PREFIX}${path}`;
  const url = API_BASE
    ? new URL(`${API_BASE}${pathWithPrefix}`)
    : new URL(pathWithPrefix, window.location.origin);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

export async function parseErrorBody(
  response: Response
): Promise<API.ErrorResponse> {
  try {
    return (await response.json()) as API.ErrorResponse;
  } catch {
    return {
      code: "HTTP_ERROR",
      message: response.statusText || `HTTP ${response.status}`,
      timestamp: new Date().toISOString(),
    };
  }
}

export async function requestJson<T>(
  path: string,
  init: RequestInit & {
    userId?: string;
    query?: Record<string, string | number | undefined>;
  } = {}
): Promise<API.ApiResponse<T>> {
  const { userId, query, headers, ...rest } = init;
  const response = await fetch(buildUrl(path, query), {
    ...rest,
    headers: {
      Accept: "application/json",
      ...(rest.body ? { "Content-Type": "application/json" } : {}),
      ...(userId ? { "X-User-Id": userId } : {}),
      ...headers,
    },
  });

  const body = (await response.json()) as API.ApiResponse<T> | API.ErrorResponse;

  if (!response.ok) {
    throw new ApiError(response.status, body as API.ErrorResponse);
  }

  return body as API.ApiResponse<T>;
}
