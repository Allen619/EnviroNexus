/** URL 查询参数名，与后端 session_id 一致 */
export const SESSION_ID_QUERY = "session_id";

export function readSessionIdFromUrl(): string {
  return (
    new URLSearchParams(window.location.search).get(SESSION_ID_QUERY)?.trim() ??
    ""
  );
}

/** 将当前选中的 session_id 写入地址栏 */
export function syncSessionIdToUrl(sessionId: string, replace = false) {
  const url = new URL(window.location.href);

  if (sessionId) {
    url.searchParams.set(SESSION_ID_QUERY, sessionId);
  } else {
    url.searchParams.delete(SESSION_ID_QUERY);
  }

  window.history[replace ? "replaceState" : "pushState"](null, "", url);
}
