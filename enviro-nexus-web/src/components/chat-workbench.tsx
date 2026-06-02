import { useCallback, useRef, useState } from "react";
import { LeafIcon } from "lucide-react";
import type { ChatStatus } from "ai";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

const SUGGESTIONS = [
  "解读一份地表水 COD 超标报告",
  "GB 3838 与 GB 8978 标准有什么区别？",
  "帮我整理 VOCs 现场采样的注意事项",
];

const SAMPLE_ANSWER = `## 地表水 COD 异常初步研判

收到该批次监测数据，**化学需氧量（COD\\_Cr）** 已超出 \\(Ⅲ\\) 类水体限值，研判如下：

### 1. 关键指标对比

| 指标 | 实测值 | Ⅲ 类限值 | 判定 |
| --- | --- | --- | --- |
| COD_Cr | 32 mg/L | 20 mg/L | 超标 |
| 氨氮 | 0.8 mg/L | 1.0 mg/L | 达标 |
| 溶解氧 | 4.1 mg/L | ≥ 5 mg/L | 偏低 |

### 2. 可能成因

1. 上游存在 **有机污染** 输入（生活污水 / 农业面源）
2. 采样前 \`48h\` 内有降雨，地表径流冲刷
3. 溶解氧偏低，提示水体自净能力下降

### 3. 建议处置

\`\`\`text
1) 复测 COD，排除采样/运输污染
2) 加密上游断面布点，溯源排查
3) 同步调取近 7 日水文与排口在线数据
\`\`\`

> 如需，我可以基于历史趋势生成溯源排查清单。`;

let idSeq = 0;
const nextId = () => `${Date.now()}-${idSeq++}`;

export function ChatWorkbench() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<ChatStatus>("ready");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const streamAnswer = useCallback(() => {
    const assistantId = nextId();
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setStatus("streaming");

    let index = 0;
    timerRef.current = setInterval(() => {
      index += 4;
      const slice = SAMPLE_ANSWER.slice(0, index);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, content: slice } : m
        )
      );
      if (index >= SAMPLE_ANSWER.length) {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = null;
        setStatus("ready");
      }
    }, 16);
  }, []);

  const send = useCallback(
    (text: string) => {
      const value = text.trim();
      if (!value || status === "streaming" || status === "submitted") return;
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: "user", content: value },
      ]);
      setStatus("submitted");
      setTimeout(streamAnswer, 250);
    },
    [status, streamAnswer]
  );

  const handleSubmit = useCallback(
    (message: PromptInputMessage) => {
      send(message.text);
    },
    [send]
  );

  const stop = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    setStatus("ready");
  }, []);

  return (
    <div className="mx-auto flex h-full w-full max-w-3xl flex-col gap-4">
      <Conversation className="flex-1 rounded-xl border bg-card">
        <ConversationContent>
          {messages.length === 0 ? (
            <ConversationEmptyState
              icon={<LeafIcon className="size-8" />}
              title="环检智枢 · AI 工作台"
              description="提出环保检测相关问题，体验流式 Markdown 渲染"
            >
              <Suggestions className="mt-4">
                {SUGGESTIONS.map((s) => (
                  <Suggestion key={s} suggestion={s} onClick={send} />
                ))}
              </Suggestions>
            </ConversationEmptyState>
          ) : (
            messages.map((m) => (
              <Message from={m.role} key={m.id}>
                <MessageContent>
                  {m.role === "assistant" ? (
                    <MessageResponse>{m.content}</MessageResponse>
                  ) : (
                    m.content
                  )}
                </MessageContent>
              </Message>
            ))
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      <PromptInput onSubmit={handleSubmit} className="rounded-xl">
        <PromptInputBody>
          <PromptInputTextarea placeholder="向环检智枢提问，例如：解读这份废水监测报告…" />
          <PromptInputFooter>
            <PromptInputTools />
            <PromptInputSubmit status={status} onStop={stop} />
          </PromptInputFooter>
        </PromptInputBody>
      </PromptInput>
    </div>
  );
}
