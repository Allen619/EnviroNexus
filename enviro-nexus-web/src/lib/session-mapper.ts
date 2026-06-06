import type {
  ChatMessage,
  ChatRole,
  ChatSession,
  ChatSource,
} from "@/lib/chat-stream";

export const sourceItemToChatSource = (
  item: API.SourceItem,
  index: number,
): ChatSource => ({
  content: item.summary || undefined,
  id: item.evidence_id ?? `src_${index}`,
  relevance: 1,
  section: item.section || undefined,
  standardNo: item.source_title || "参考来源",
  title: item.summary || item.source_title || "参考来源",
});

export const apiMessageToChatMessage = (
  message: Sessions.ChatMessage,
  sessionId: string,
  index: number,
  baseTime: number,
): ChatMessage => ({
  content: message.content,
  createdAt: baseTime + index,
  id: `${sessionId}_msg_${index}`,
  role: (message.role === "assistant" ? "assistant" : "user") as ChatRole,
  sources:
    message.role === "assistant" && message.sources?.length
      ? message.sources.map(sourceItemToChatSource)
      : undefined,
  status: "ready",
});

const stripThinkTags = (text: string) =>
  text
    .replace(/<think>[\s\S]*?<\/think>/gi, "")
    .replace(/<think>[\s\S]*$/gi, "")
    .replace(/<\/think>/gi, "")
    .trim();

const stripThinkTitlePrefix = (text: string) =>
  text.replace(/^<think>\r?\n?/i, "").trim();

const titleFromMessages = (messages: ChatMessage[]) =>
  messages.find((message) => message.role === "user")?.content.trim();

export const sessionDetailToChatSession = (
  detail: Sessions.SessionDetailData,
): ChatSession => {
  const baseTime = new Date(detail.updated_at).getTime();
  const messages = (detail.messages ?? []).map((message, index) =>
    apiMessageToChatMessage(message, detail.session_id, index, baseTime),
  );

  return {
    createdAt: new Date(detail.created_at).getTime(),
    id: detail.session_id,
    messages,
    title: titleFromMessages(messages) || stripThinkTags(detail.title || "") || "新对话",
    updatedAt: baseTime,
  };
};

export const sessionSummaryToChatSession = (
  item: Sessions.SessionSummary,
): ChatSession => ({
  createdAt: new Date(item.created_at).getTime(),
  id: item.session_id,
  messages: [],
  title: stripThinkTitlePrefix(item.title || "") || "新对话",
  updatedAt: new Date(item.updated_at).getTime(),
});
