import type { ChatSession } from "@/lib/chat-stream";

export const toTitle = (text: string) =>
  text.length > 24 ? `${text.slice(0, 24)}...` : text;

export const stripThinkTags = (text: string) =>
  text
    .replace(/<think>[\s\S]*?<\/think>/gi, "")
    .replace(/<think>[\s\S]*$/gi, "")
    .replace(/<\/think>/gi, "")
    .trim();

export const getSessionDisplayTitle = (session: ChatSession) =>
  toTitle(
    session.messages
      .find((message) => message.role === "user")
      ?.content.trim() ||
      stripThinkTags(session.title) ||
      "新对话",
  );
