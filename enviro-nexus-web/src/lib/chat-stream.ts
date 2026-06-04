export type ChatRequestStatus = "ready" | "submitted" | "streaming" | "error";

export type ChatMessageStatus = "streaming" | "ready" | "error" | "stopped";

export type ChatRole = "user" | "assistant";

export type ChatSource = {
  id: string;
  title: string;
  standardNo: string;
  standardName?: string;
  section?: string;
  content?: string;
  highlights?: string[];
  relevance: number;
  url?: string;
};

export type ChatFollowup = {
  id: string;
  text: string;
};

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  status?: ChatMessageStatus;
  requestId?: string;
  createdAt: number;
  sources?: ChatSource[];
  followups?: ChatFollowup[];
  errorMessage?: string;
};

export type ChatSession = {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
  /** 是否已从 GET /sessions/{id} 拉取过完整消息 */
  messagesLoaded?: boolean;
};

export type ChatRequest = {
  requestId: string;
  assistantMessageId: string;
  sessionId: string;
  message: string;
  messages: Array<{
    id: string;
    role: ChatRole;
    content: string;
  }>;
  options?: {
    includeSources?: boolean;
    includeFollowups?: boolean;
  };
};

export type ChatStreamDelta = {
  type: "delta";
  requestId: string;
  assistantMessageId: string;
  content: string;
};

export type ChatStreamDone = {
  type: "done";
  requestId: string;
  assistantMessageId: string;
  sessionId: string;
  sessionTitle?: string;
  sources: ChatSource[];
  followups: ChatFollowup[];
};

export type ChatStreamError = {
  type: "error";
  requestId: string;
  assistantMessageId: string;
  code:
    | "BAD_REQUEST"
    | "UNAUTHORIZED"
    | "RATE_LIMITED"
    | "RAG_UNAVAILABLE"
    | "MODEL_UNAVAILABLE"
    | "INTERNAL_ERROR";
  message: string;
  retryable: boolean;
};

export type ChatStreamEvent =
  | ChatStreamDelta
  | ChatStreamDone
  | ChatStreamError;

type StreamChatOptions = {
  endpoint?: string;
  request: ChatRequest;
  signal?: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
};

type ErrorBody = {
  code?: string;
  message?: string;
  success?: boolean;
  error?: {
    message?: string;
  };
};

type ApiEnvelope = {
  success: boolean;
  code: string;
  message: string;
  data?: Record<string, unknown>;
};

const DEFAULT_ENDPOINT = "/api/chat";

const readErrorMessage = async (response: Response) => {
  try {
    const body = (await response.json()) as ErrorBody;
    return body.error?.message || body.message || `服务返回 ${response.status}`;
  } catch {
    return `服务返回 ${response.status}`;
  }
};

const isJsonResponse = (response: Response) =>
  response.headers.get("content-type")?.includes("application/json");

const readTextContent = (data: Record<string, unknown>) => {
  for (const key of ["content", "answer", "text", "markdown"]) {
    if (typeof data[key] === "string") {
      return data[key];
    }
  }

  return "";
};

const handleJsonEnvelope = (
  envelope: ApiEnvelope,
  request: ChatRequest,
  onEvent: (event: ChatStreamEvent) => void
) => {
  if (!envelope.success || envelope.code === "DEGRADED") {
    throw new Error(envelope.message || "知识服务不可用");
  }

  const data = envelope.data ?? {};
  const content = readTextContent(data);

  if (content) {
    onEvent({
      assistantMessageId: request.assistantMessageId,
      content,
      requestId: request.requestId,
      type: "delta",
    });
  }

  onEvent({
    assistantMessageId: request.assistantMessageId,
    followups: Array.isArray(data.followups)
      ? (data.followups as ChatFollowup[])
      : [],
    requestId: request.requestId,
    sessionId: request.sessionId,
    sessionTitle:
      typeof data.sessionTitle === "string" ? data.sessionTitle : undefined,
    sources: Array.isArray(data.sources) ? (data.sources as ChatSource[]) : [],
    type: "done",
  });
};

const parseSseBlock = (block: string) => {
  let eventName = "message";
  const dataLines: string[] = [];

  for (const rawLine of block.split(/\r?\n/)) {
    const line = rawLine.trimEnd();

    if (!line || line.startsWith(":")) {
      continue;
    }

    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
      continue;
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    data: dataLines.join("\n"),
    eventName,
  };
};

const toStreamEvent = (
  eventName: string,
  data: string
): ChatStreamEvent | null => {
  if (eventName === "ping") {
    return null;
  }

  const parsed = JSON.parse(data) as Record<string, unknown>;

  if (eventName === "delta") {
    return {
      assistantMessageId: String(parsed.assistantMessageId ?? ""),
      content: String(parsed.content ?? ""),
      requestId: String(parsed.requestId ?? ""),
      type: "delta",
    };
  }

  if (eventName === "done") {
    return {
      assistantMessageId: String(parsed.assistantMessageId ?? ""),
      followups: Array.isArray(parsed.followups)
        ? (parsed.followups as ChatFollowup[])
        : [],
      requestId: String(parsed.requestId ?? ""),
      sessionId: String(parsed.sessionId ?? ""),
      sessionTitle:
        typeof parsed.sessionTitle === "string"
          ? parsed.sessionTitle
          : undefined,
      sources: Array.isArray(parsed.sources)
        ? (parsed.sources as ChatSource[])
        : [],
      type: "done",
    };
  }

  if (eventName === "error") {
    return {
      assistantMessageId: String(parsed.assistantMessageId ?? ""),
      code: (parsed.code as ChatStreamError["code"]) || "INTERNAL_ERROR",
      message: String(parsed.message || "生成失败"),
      requestId: String(parsed.requestId ?? ""),
      retryable: Boolean(parsed.retryable),
      type: "error",
    };
  }

  return null;
};

export async function streamChat({
  endpoint = DEFAULT_ENDPOINT,
  request,
  signal,
  onEvent,
}: StreamChatOptions) {
  const response = await fetch(endpoint, {
    body: JSON.stringify(request),
    headers: {
      Accept: "text/event-stream, application/json",
      "Content-Type": "application/json",
    },
    method: "POST",
    signal,
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  if (isJsonResponse(response)) {
    const envelope = (await response.json()) as ApiEnvelope;
    handleJsonEnvelope(envelope, request, onEvent);
    return;
  }

  if (!response.body) {
    throw new Error("服务未返回可读取的流式响应");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let receivedDone = false;

  const processBlock = (block: string) => {
    const parsed = parseSseBlock(block);

    if (!parsed) {
      return;
    }

    const event = toStreamEvent(parsed.eventName, parsed.data);

    if (!event) {
      return;
    }

    if (event.type === "done") {
      receivedDone = true;
    }

    onEvent(event);
  };

  while (true) {
    const { done, value } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      processBlock(block);
    }
  }

  buffer += decoder.decode();

  if (buffer.trim()) {
    processBlock(buffer);
  }

  if (!receivedDone && !signal?.aborted) {
    throw new Error("连接在回复完成前中断");
  }
}
