import { useCallback, useMemo, useRef, useState } from "react";
import type { ChatStatus } from "ai";
import {
  BookOpenIcon,
  LeafIcon,
  MessageSquareIcon,
  PlusIcon,
  Trash2Icon,
} from "lucide-react";
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
  PromptInputSubmit,
  PromptInputTextarea,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import {
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "@/components/ai-elements/sources";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  type ChatMessage,
  type ChatRequestStatus,
  type ChatSession,
  type ChatSource,
  streamChat,
} from "@/lib/chat-stream";
import { cn } from "@/lib/utils";

const SUGGESTIONS = [
  "COD 检测用什么标准方法？",
  "GB 3838 与 GB 8978 标准有什么区别？",
  "帮我整理 VOCs 现场采样的注意事项",
];

const createId = (prefix: string) =>
  `${prefix}_${Date.now().toString(36)}_${crypto.randomUUID().slice(0, 8)}`;

const createSession = (): ChatSession => {
  const now = Date.now();

  return {
    createdAt: now,
    id: createId("session"),
    messages: [],
    title: "新对话",
    updatedAt: now,
  };
};

const toTitle = (text: string) =>
  text.length > 24 ? `${text.slice(0, 24)}...` : text;

const formatRelevance = (value: number) => `${Math.round(value * 100)}%`;

type ActiveRequest = {
  assistantMessageId: string;
  controller: AbortController;
  requestId: string;
  sessionId: string;
};

function SourceDetailDialog({
  onOpenChange,
  source,
}: {
  onOpenChange: (open: boolean) => void;
  source: ChatSource | null;
}) {
  return (
    <Dialog onOpenChange={onOpenChange} open={Boolean(source)}>
      <DialogContent className="max-h-[80vh] overflow-hidden sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{source?.standardNo || source?.title}</DialogTitle>
          <DialogDescription>
            {source?.standardName || source?.title || "参考来源详情"}
          </DialogDescription>
        </DialogHeader>
        {source && (
          <div className="grid gap-4 overflow-y-auto pr-1">
            <div className="grid gap-2 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">
                  {source.section || "未标注章节"}
                </Badge>
                <Badge variant="outline">
                  相关度 {formatRelevance(source.relevance)}
                </Badge>
              </div>
              <p className="font-medium">{source.title}</p>
            </div>

            {source.highlights && source.highlights.length > 0 && (
              <div className="grid gap-2">
                <p className="text-muted-foreground text-xs">高亮关键词</p>
                <div className="flex flex-wrap gap-2">
                  {source.highlights.map((highlight) => (
                    <Badge key={highlight} variant="outline">
                      {highlight}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            <div className="grid gap-2">
              <p className="text-muted-foreground text-xs">原文片段</p>
              <div className="whitespace-pre-wrap rounded-lg border bg-muted/40 p-3 text-sm leading-6">
                {source.content || "暂无可展示原文"}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function ChatWorkbench() {
  const initialSession = useMemo(() => createSession(), []);
  const [sessions, setSessions] = useState<ChatSession[]>([initialSession]);
  const [activeSessionId, setActiveSessionId] = useState(initialSession.id);
  const [inputValue, setInputValue] = useState("");
  const [requestStatus, setRequestStatus] =
    useState<ChatRequestStatus>("ready");
  const [selectedSource, setSelectedSource] = useState<ChatSource | null>(null);
  const [activeRequestSessionId, setActiveRequestSessionId] = useState<
    string | null
  >(null);
  const activeRequestRef = useRef<ActiveRequest | null>(null);

  const activeSession = useMemo(
    () =>
      sessions.find((session) => session.id === activeSessionId) ??
      sessions[0] ??
      initialSession,
    [activeSessionId, initialSession, sessions]
  );

  const chatStatus: ChatStatus =
    requestStatus === "ready"
      ? "ready"
      : requestStatus === "error"
        ? "error"
        : requestStatus === "submitted"
          ? "submitted"
          : "streaming";

  const updateSession = useCallback(
    (sessionId: string, updater: (session: ChatSession) => ChatSession) => {
      setSessions((prev) =>
        prev.map((session) =>
          session.id === sessionId ? updater(session) : session
        )
      );
    },
    []
  );

  const updateAssistantMessage = useCallback(
    (
      sessionId: string,
      messageId: string,
      updater: (message: ChatMessage) => ChatMessage
    ) => {
      updateSession(sessionId, (session) => ({
        ...session,
        messages: session.messages.map((message) =>
          message.id === messageId ? updater(message) : message
        ),
        updatedAt: Date.now(),
      }));
    },
    [updateSession]
  );

  const isCurrentEvent = useCallback(
    (requestId: string, assistantMessageId: string) => {
      const activeRequest = activeRequestRef.current;

      return (
        activeRequest?.requestId === requestId &&
        activeRequest.assistantMessageId === assistantMessageId
      );
    },
    []
  );

  const stopGeneration = useCallback(() => {
    const activeRequest = activeRequestRef.current;

    if (!activeRequest) {
      return;
    }

    activeRequest.controller.abort();
    activeRequestRef.current = null;
    setActiveRequestSessionId(null);
    updateAssistantMessage(
      activeRequest.sessionId,
      activeRequest.assistantMessageId,
      (message) => ({
        ...message,
        status: "stopped",
      })
    );
    setRequestStatus("ready");
  }, [updateAssistantMessage]);

  const send = useCallback(
    (text: string) => {
      const value = text.trim();

      if (!value || !activeSession || requestStatus !== "ready") {
        return;
      }

      const now = Date.now();
      const requestId = createId("req");
      const userMessage: ChatMessage = {
        content: value,
        createdAt: now,
        id: createId("msg_user"),
        role: "user",
      };
      const assistantMessage: ChatMessage = {
        content: "",
        createdAt: now,
        id: createId("msg_assistant"),
        requestId,
        role: "assistant",
        status: "streaming",
      };
      const nextMessages = [...activeSession.messages, userMessage];
      const controller = new AbortController();

      setSessions((prev) =>
        prev.map((session) => {
          if (session.id !== activeSession.id) {
            return session;
          }

          return {
            ...session,
            messages: [...nextMessages, assistantMessage],
            title:
              session.messages.length === 0 || session.title === "新对话"
                ? toTitle(value)
                : session.title,
            updatedAt: now,
          };
        })
      );

      activeRequestRef.current = {
        assistantMessageId: assistantMessage.id,
        controller,
        requestId,
        sessionId: activeSession.id,
      };
      setActiveRequestSessionId(activeSession.id);
      setRequestStatus("submitted");

      void streamChat({
        request: {
          assistantMessageId: assistantMessage.id,
          message: value,
          messages: nextMessages.map((message) => ({
            content: message.content,
            id: message.id,
            role: message.role,
          })),
          options: {
            includeFollowups: true,
            includeSources: true,
          },
          requestId,
          sessionId: activeSession.id,
        },
        signal: controller.signal,
        onEvent: (event) => {
          if (!isCurrentEvent(event.requestId, event.assistantMessageId)) {
            return;
          }

          if (event.type === "delta") {
            setRequestStatus("streaming");
            updateAssistantMessage(
              activeSession.id,
              assistantMessage.id,
              (message) => {
                if (message.status !== "streaming") {
                  return message;
                }

                return {
                  ...message,
                  content: `${message.content}${event.content}`,
                };
              }
            );
            return;
          }

          if (event.type === "done") {
            activeRequestRef.current = null;
            setActiveRequestSessionId(null);
            setRequestStatus("ready");
            updateSession(activeSession.id, (session) => ({
              ...session,
              messages: session.messages.map((message) =>
                message.id === assistantMessage.id
                  ? {
                      ...message,
                      followups: event.followups,
                      sources: event.sources,
                      status: "ready",
                    }
                  : message
              ),
              title: event.sessionTitle || session.title,
              updatedAt: Date.now(),
            }));
            return;
          }

          activeRequestRef.current = null;
          setActiveRequestSessionId(null);
          setRequestStatus("ready");
          updateAssistantMessage(
            activeSession.id,
            assistantMessage.id,
            (message) => ({
              ...message,
              content: message.content || event.message,
              errorMessage: event.message,
              status: "error",
            })
          );
        },
      }).catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }

        if (!isCurrentEvent(requestId, assistantMessage.id)) {
          return;
        }

        const message =
          error instanceof Error ? error.message : "生成失败，请稍后重试";

        activeRequestRef.current = null;
        setActiveRequestSessionId(null);
        setRequestStatus("ready");
        updateAssistantMessage(
          activeSession.id,
          assistantMessage.id,
          (assistant) => ({
            ...assistant,
            content: assistant.content || message,
            errorMessage: message,
            status: "error",
          })
        );
      });
    },
    [
      activeSession,
      isCurrentEvent,
      requestStatus,
      updateAssistantMessage,
      updateSession,
    ]
  );

  const handleSubmit = useCallback(
    (message: PromptInputMessage) => {
      send(message.text);
      setInputValue("");
    },
    [send]
  );

  const createNewSession = useCallback(() => {
    if (activeRequestRef.current) {
      stopGeneration();
    }

    const session = createSession();
    setSessions((prev) => [session, ...prev]);
    setActiveSessionId(session.id);
  }, [stopGeneration]);

  const switchSession = useCallback(
    (sessionId: string) => {
      if (sessionId === activeSessionId) {
        return;
      }

      if (activeRequestRef.current) {
        stopGeneration();
      }

      setActiveSessionId(sessionId);
    },
    [activeSessionId, stopGeneration]
  );

  const deleteSession = useCallback(
    (sessionId: string) => {
      if (activeRequestRef.current?.sessionId === sessionId) {
        return;
      }

      const session = sessions.find((item) => item.id === sessionId);

      if (!session) {
        return;
      }

      if (!window.confirm(`删除“${session.title}”？此操作不会保留该会话。`)) {
        return;
      }

      setSessions((prev) => {
        const next = prev.filter((item) => item.id !== sessionId);

        if (next.length > 0) {
          if (activeSessionId === sessionId) {
            setActiveSessionId(next[0].id);
          }

          return next;
        }

        const fallback = createSession();
        setActiveSessionId(fallback.id);
        return [fallback];
      });
    },
    [activeSessionId, sessions]
  );

  return (
    <div className="flex h-screen min-h-0 bg-background text-foreground">
      <aside className="hidden w-72 shrink-0 border-r bg-muted/25 p-3 md:flex md:flex-col">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 font-medium">
            <LeafIcon className="size-4" />
            环检智枢
          </div>
          <Button
            aria-label="新建对话"
            onClick={createNewSession}
            size="icon-sm"
            type="button"
          >
            <PlusIcon className="size-4" />
          </Button>
        </div>

        <div className="mt-4 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
          {sessions.map((session) => (
            <div
              className={cn(
                "group flex items-center gap-2 rounded-lg px-2 py-2 text-left text-sm",
                session.id === activeSessionId
                  ? "bg-background shadow-xs"
                  : "hover:bg-background/70"
              )}
              key={session.id}
            >
              <button
                className="flex min-w-0 flex-1 items-center gap-2 text-left"
                onClick={() => switchSession(session.id)}
                type="button"
              >
                <MessageSquareIcon className="size-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{session.title}</span>
              </button>
              <Button
                aria-label="删除对话"
                className="opacity-0 group-hover:opacity-100"
                disabled={activeRequestSessionId === session.id}
                onClick={() => deleteSession(session.id)}
                size="icon-xs"
                type="button"
                variant="ghost"
              >
                <Trash2Icon className="size-3" />
              </Button>
            </div>
          ))}
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between border-b px-4">
          <div>
            <h1 className="font-medium">环检智枢 · AI 工作台</h1>
            <p className="text-muted-foreground text-xs">
              基于标准方法知识库的环保检测问答
            </p>
          </div>
          <Button
            className="md:hidden"
            onClick={createNewSession}
            size="sm"
            type="button"
          >
            <PlusIcon className="size-4" />
            新建
          </Button>
        </header>

        <div className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col gap-3 p-3 md:p-4">
          <Conversation className="min-h-0 flex-1 rounded-lg border bg-card">
            <ConversationContent>
              {activeSession.messages.length === 0 ? (
                <ConversationEmptyState
                  description="查询检测标准、采样注意事项、报告异常研判和方法适用范围。"
                  icon={<LeafIcon className="size-8" />}
                  title="环检智枢 · AI 工作台"
                >
                  <div className="text-muted-foreground">
                    <LeafIcon className="size-8" />
                  </div>
                  <div className="space-y-1">
                    <h2 className="font-medium text-sm">
                      环检智枢 · AI 工作台
                    </h2>
                    <p className="text-muted-foreground text-sm">
                      查询检测标准、采样注意事项、报告异常研判和方法适用范围。
                    </p>
                  </div>
                  <Suggestions className="mt-4">
                    {SUGGESTIONS.map((suggestion) => (
                      <Suggestion
                        disabled={requestStatus !== "ready"}
                        key={suggestion}
                        onClick={send}
                        suggestion={suggestion}
                      />
                    ))}
                  </Suggestions>
                </ConversationEmptyState>
              ) : (
                activeSession.messages.map((message) => (
                  <Message from={message.role} key={message.id}>
                    <MessageContent>
                      {message.role === "assistant" ? (
                        <>
                          <MessageResponse>{message.content}</MessageResponse>
                          {message.status === "stopped" && (
                            <Badge className="w-fit" variant="outline">
                              已停止生成
                            </Badge>
                          )}
                          {message.status === "error" &&
                            message.errorMessage && (
                              <Badge className="w-fit" variant="destructive">
                                {message.errorMessage}
                              </Badge>
                            )}
                          {message.status === "ready" &&
                            message.sources &&
                            message.sources.length > 0 && (
                              <Sources className="mt-2 mb-0">
                                <SourcesTrigger count={message.sources.length} />
                                <SourcesContent className="w-full">
                                  {message.sources.map((source) => (
                                    <Source
                                      className="w-full rounded-lg border bg-background p-2 text-left hover:bg-muted"
                                      href={source.url || "#"}
                                      key={source.id}
                                      onClick={(event) => {
                                        event.preventDefault();
                                        setSelectedSource(source);
                                      }}
                                      title={source.title}
                                    >
                                      <BookOpenIcon className="size-4 shrink-0" />
                                      <span className="min-w-0">
                                        <span className="block truncate font-medium">
                                          {source.standardNo} ·{" "}
                                          {source.section || "章节未标注"}
                                        </span>
                                        <span className="block truncate text-muted-foreground">
                                          {source.title}
                                        </span>
                                      </span>
                                    </Source>
                                  ))}
                                </SourcesContent>
                              </Sources>
                            )}
                          {message.status === "ready" &&
                            message.followups &&
                            message.followups.length > 0 && (
                              <Suggestions className="mt-2">
                                {message.followups.map((followup) => (
                                  <Suggestion
                                    disabled={requestStatus !== "ready"}
                                    key={followup.id}
                                    onClick={send}
                                    suggestion={followup.text}
                                    variant="secondary"
                                  />
                                ))}
                              </Suggestions>
                            )}
                        </>
                      ) : (
                        message.content
                      )}
                    </MessageContent>
                  </Message>
                ))
              )}
            </ConversationContent>
            <ConversationScrollButton />
          </Conversation>

          <PromptInput
            onSubmit={handleSubmit}
            className="relative z-10 shrink-0 rounded-lg bg-background"
          >
            <PromptInputBody>
              <PromptInputTextarea
                className="min-h-20 w-full px-3 py-3 pr-14 pb-10"
                disabled={requestStatus !== "ready"}
                onChange={(event) => setInputValue(event.currentTarget.value)}
                placeholder="向环检智枢提问，例如：COD 检测用什么标准方法？"
                value={inputValue}
              />
              <PromptInputSubmit
                className="absolute right-2 bottom-2 z-10"
                onStop={stopGeneration}
                status={chatStatus}
              />
            </PromptInputBody>
          </PromptInput>
        </div>
      </main>

      <SourceDetailDialog
        onOpenChange={(open) => {
          if (!open) {
            setSelectedSource(null);
          }
        }}
        source={selectedSource}
      />
    </div>
  );
}
