import {
  ApiError,
  type ApiClientOptions,
  buildUrl,
  parseErrorBody,
  requestJson,
} from "../client";

/** POST /api/v1/factors/query — 会话内因子查询（非流式） */
export function queryFactor(
  body: Factors.FactorQueryRequest,
  options: ApiClientOptions,
) {
  return requestJson<Factors.FactorQueryData>("/factors/query", {
    method: "POST",
    userId: options.userId,
    signal: options.signal,
    body: JSON.stringify(body),
  });
}

/** GET /api/v1/method-cards/{card_id} — 方法卡详情 */
export function getMethodCard(
  cardId: string,
  options?: { signal?: AbortSignal },
) {
  return requestJson<Factors.MethodCardData>(
    `/method-cards/${encodeURIComponent(cardId)}`,
    {
      method: "GET",
      signal: options?.signal,
    },
  );
}

type ParseSseBlock = { eventName: string; data: string } | null;

function parseSseBlock(block: string): ParseSseBlock {
  let eventName = "message";
  const dataLines: string[] = [];

  for (const rawLine of block.split(/\r?\n/)) {
    const line = rawLine.trimEnd();
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) return null;
  return { eventName, data: dataLines.join("\n") };
}

function toFactorStreamEvent(
  eventName: string,
  data: string,
): Factors.FactorStreamEvent | null {
  const parsed = JSON.parse(data) as Record<string, unknown>;
  switch (eventName) {
    case "meta":
      return { event: "meta", data: parsed as Factors.StreamMetaEvent };
    case "token":
      return { event: "token", data: parsed as Factors.StreamTokenEvent };
    case "done":
      return { event: "done", data: parsed as Factors.StreamDoneEvent };
    case "error":
      return { event: "error", data: parsed as Factors.StreamErrorEvent };
    default:
      return null;
  }
}

export type QueryFactorStreamOptions = ApiClientOptions & {
  onEvent: (event: Factors.FactorStreamEvent) => void;
};

/**
 * POST /api/v1/factors/query/stream — 会话内因子查询（SSE）
 * 流前错误为 JSON，会抛出 ApiError。
 */
export async function queryFactorStream(
  body: Factors.FactorQueryRequest,
  options: QueryFactorStreamOptions,
) {
  const response = await fetch(buildUrl("/factors/query/stream"), {
    method: "POST",
    headers: {
      Accept: "text/event-stream, application/json",
      "Content-Type": "application/json",
      "X-User-Id": options.userId,
    },
    body: JSON.stringify(body),
    signal: options.signal,
  });

  const contentType = response.headers.get("content-type") ?? "";

  if (!response.ok || contentType.includes("application/json")) {
    throw new ApiError(response.status, await parseErrorBody(response));
  }

  if (!response.body) {
    throw new Error("服务未返回可读取的流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let receivedDone = false;

  const emitBlock = (block: string) => {
    const parsed = parseSseBlock(block);
    if (!parsed) return;

    const event = toFactorStreamEvent(parsed.eventName, parsed.data);
    if (!event) return;

    if (event.event === "done") receivedDone = true;
    if (event.event === "error") {
      options.onEvent(event);
      throw new Error(event.data.message || event.data.code);
    }
    options.onEvent(event);
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      emitBlock(block);
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) {
    emitBlock(buffer);
  }

  if (!receivedDone && !options.signal?.aborted) {
    throw new Error("连接在回复完成前中断");
  }
}
