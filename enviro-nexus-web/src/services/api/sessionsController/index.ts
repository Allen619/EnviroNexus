import { type ApiClientOptions, requestJson } from "../client";

/** POST /api/v1/sessions — 创建新会话 */
export function createSession(options: ApiClientOptions) {
  return requestJson<Sessions.SessionDetailData>("/sessions", {
    method: "POST",
    userId: options.userId,
    signal: options.signal,
  });
}

const createSessionInflight = new Map<
  string,
  Promise<API.ApiResponse<Sessions.SessionDetailData>>
>();

/** 创建会话（进行中去重，避免 StrictMode 重复创建） */
export function createSessionOnce(options: ApiClientOptions) {
  const key = options.userId;
  let pending = createSessionInflight.get(key);
  if (!pending) {
    pending = createSession(options).finally(() => {
      createSessionInflight.delete(key);
    });
    createSessionInflight.set(key, pending);
  }
  return pending;
}

/** GET /api/v1/sessions — 历史会话列表 */
export function listSessions(
  options: ApiClientOptions & { params?: Sessions.ListSessionsParams },
) {
  const { page, page_size } = options.params ?? {};
  return requestJson<Sessions.SessionListData>("/sessions", {
    method: "GET",
    userId: options.userId,
    signal: options.signal,
    query: { page, page_size },
  });
}

function listSessionsCacheKey(
  options: ApiClientOptions & { params?: Sessions.ListSessionsParams },
) {
  const { page = 1, page_size = 20 } = options.params ?? {};
  return `${options.userId}:${page}:${page_size}`;
}

const listSessionsInflight = new Map<
  string,
  Promise<API.ApiResponse<Sessions.SessionListData>>
>();

/**
 * 历史会话列表（进行中去重）
 * 开发环境 React StrictMode 会双重挂载，避免同一参数并发打两次接口。
 */
export function listSessionsOnce(
  options: ApiClientOptions & { params?: Sessions.ListSessionsParams },
) {
  const key = listSessionsCacheKey(options);
  let pending = listSessionsInflight.get(key);
  if (!pending) {
    pending = listSessions(options).finally(() => {
      listSessionsInflight.delete(key);
    });
    listSessionsInflight.set(key, pending);
  }
  return pending;
}

/** 清空会话相关请求缓存（删除/新建后调用） */
export function invalidateSessionListCache() {
  listSessionsInflight.clear();
  getSessionInflight.clear();
}

/** GET /api/v1/sessions/{session_id} — 会话详情 */
export function getSession(sessionId: string, options: ApiClientOptions) {
  return requestJson<Sessions.SessionDetailData>(
    `/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: "GET",
      userId: options.userId,
      signal: options.signal,
    },
  );
}

const getSessionInflight = new Map<
  string,
  Promise<API.ApiResponse<Sessions.SessionDetailData>>
>();

function getSessionCacheKey(sessionId: string, userId: string) {
  return `${userId}:${sessionId}`;
}

/** 会话详情（进行中去重） */
export function getSessionOnce(sessionId: string, options: ApiClientOptions) {
  const key = getSessionCacheKey(sessionId, options.userId);
  let pending = getSessionInflight.get(key);
  if (!pending) {
    pending = getSession(sessionId, options).finally(() => {
      getSessionInflight.delete(key);
    });
    getSessionInflight.set(key, pending);
  }
  return pending;
}

/** DELETE /api/v1/sessions/{session_id} — 删除会话 */
export function deleteSession(sessionId: string, options: ApiClientOptions) {
  return requestJson<Sessions.SessionDeleteData>(
    `/sessions/${encodeURIComponent(sessionId)}`,
    {
      method: "DELETE",
      userId: options.userId,
      signal: options.signal,
    },
  );
}
