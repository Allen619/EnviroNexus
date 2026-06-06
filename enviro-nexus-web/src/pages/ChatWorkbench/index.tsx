import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChatStatus } from "ai";
import { LeafIcon, PlusIcon } from "lucide-react";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { Message, MessageContent } from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputBody,
  PromptInputSubmit,
  PromptInputTextarea,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { Button } from "@/components/ui/button";
import {
  type ChatMessage,
  type ChatRequestStatus,
  type ChatSession,
  type ChatSource,
} from "@/lib/chat-stream";
import {
  sessionDetailToChatSession,
  sessionSummaryToChatSession,
  sourceItemToChatSource,
} from "@/lib/session-mapper";
import { readSessionIdFromUrl, syncSessionIdToUrl } from "@/lib/session-url";
import { toast } from "sonner";
import {
  ApiError,
  createSession,
  createSessionOnce,
  deleteSession as deleteSessionApi,
  getSession,
  invalidateSessionListCache,
  listSessionsOnce,
  queryFactorStream,
} from "@/services/api";
import AssistantMessage from "./components/AssistantMessage";
import SessionSidebar from "./components/SessionSidebar";
import SourceDetailDialog from "./components/SourceDetailDialog";
import { getSessionDisplayTitle, stripThinkTags, toTitle } from "./utils";

/** 与 API README 示例一致，可通过 VITE_USER_ID 覆盖 */
const DEFAULT_USER_ID =
  (import.meta.env.VITE_USER_ID as string | undefined) ?? "user-001";

const SUGGESTIONS = [
  "水样 pH 值检测按哪个标准做？",
  "CODMn 高锰酸盐指数的测定步骤是什么？",
  "色度样品检测前需要怎么处理？",
  "林格曼黑度现场观测有什么要求？",
  "非甲烷总烃采样和分析要注意什么？",
];
const SUGGESTION_DISPLAY_COUNT = 3;

const createId = (prefix: string) =>
  `${prefix}_${Date.now().toString(36)}_${crypto.randomUUID().slice(0, 8)}`;

const pickRandomSuggestions = () =>
  [...SUGGESTIONS]
    .sort(() => Math.random() - 0.5)
    .slice(0, SUGGESTION_DISPLAY_COUNT);

const apiErrorMessage = (error: unknown, fallback: string) =>
  error instanceof ApiError
    ? error.message
    : error instanceof Error
      ? error.message
      : fallback;

async function requestNewSession(userId: string) {
  const response = await createSession({ userId });
  const detail = response.data;

  if (!detail?.session_id) {
    throw new Error("创建会话失败：未返回 session_id");
  }

  invalidateSessionListCache();
  return sessionDetailToChatSession(detail);
}

/** 本地临时 id（非服务端 UUID）时需先 POST /sessions */
const isLocalSessionId = (sessionId: string) =>
  sessionId.startsWith("session_");

async function ensureServerSession(
  session: ChatSession,
  userId: string,
): Promise<ChatSession> {
  if (!isLocalSessionId(session.id)) {
    return session;
  }

  const created = await requestNewSession(userId);
  return { ...created, messages: session.messages };
}

const toSessionListItem = (session: ChatSession): ChatSession => ({
  ...session,
  messages: [],
});

type ActiveRequest = {
  assistantMessageId: string;
  controller: AbortController;
  requestId: string;
  sessionId: string;
};

const ChatWorkbench = () => {
  const [sessionList, setSessionList] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [activeSessionId, setActiveSessionId] = useState(() =>
    readSessionIdFromUrl(),
  );
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [creatingSession, setCreatingSession] = useState(false);
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(
    null,
  );
  const detailAbortRef = useRef<AbortController | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [requestStatus, setRequestStatus] =
    useState<ChatRequestStatus>("ready");
  const [selectedSource, setSelectedSource] = useState<ChatSource | null>(null);
  const [activeRequestSessionId, setActiveRequestSessionId] = useState<
    string | null
  >(null);
  const activeRequestRef = useRef<ActiveRequest | null>(null);
  const suggestedQuestions = useMemo(() => pickRandomSuggestions(), []);

  const detailLoading =
    Boolean(activeSessionId) && loadingSessionId === activeSessionId;

  const loadSessionDetail = useCallback(async (sessionId: string) => {
    if (!sessionId) {
      return;
    }

    detailAbortRef.current?.abort();
    const controller = new AbortController();
    detailAbortRef.current = controller;
    setActiveSession(null);
    setLoadingSessionId(sessionId);

    try {
      const response = await getSession(sessionId, {
        signal: controller.signal,
        userId: DEFAULT_USER_ID,
      });
      const detail = response.data;
      if (!detail?.session_id) {
        throw new Error("加载会话详情失败");
      }

      const full = sessionDetailToChatSession(detail);
      setActiveSession(full);
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }
      toast.error(apiErrorMessage(error, "加载会话详情失败"));
    } finally {
      if (detailAbortRef.current === controller) {
        detailAbortRef.current = null;
        setLoadingSessionId((current) =>
          current === sessionId ? null : current,
        );
      }
    }
  }, []);

  const selectSession = useCallback(
    (sessionId: string, options?: { replace?: boolean }) => {
      setActiveSessionId(sessionId);
      syncSessionIdToUrl(sessionId, options?.replace ?? false);
    },
    [],
  );

  useEffect(() => {
    const onPopState = () => {
      const sessionId = readSessionIdFromUrl();
      setActiveSessionId(sessionId);
      if (sessionId) {
        void loadSessionDetail(sessionId);
      } else {
        setActiveSession(null);
      }
    };

    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [loadSessionDetail]);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      setSessionsLoading(true);
      setSessionsError(null);

      const urlSessionId = readSessionIdFromUrl();

      try {
        const response = await listSessionsOnce({ userId: DEFAULT_USER_ID });
        if (cancelled) return;

        const items = response.data?.items ?? [];

        if (items.length === 0) {
          const created = await createSessionOnce({ userId: DEFAULT_USER_ID });
          if (cancelled) return;

          const detail = created.data;
          if (!detail?.session_id) {
            throw new Error("创建会话失败：未返回 session_id");
          }

          const session = sessionDetailToChatSession(detail);
          setSessionList([toSessionListItem(session)]);
          setActiveSession(session);
          selectSession(session.id, { replace: true });
          return;
        }

        let mapped = items.map(sessionSummaryToChatSession);
        let targetId = mapped[0].id;

        if (urlSessionId) {
          const inList = mapped.some((session) => session.id === urlSessionId);
          if (inList) {
            targetId = urlSessionId;
          } else {
            try {
              const detailRes = await getSession(urlSessionId, {
                userId: DEFAULT_USER_ID,
              });
              if (cancelled) return;

              const detail = detailRes.data;
              if (detail?.session_id) {
                const full = sessionDetailToChatSession(detail);
                mapped = [toSessionListItem(full), ...mapped];
                targetId = urlSessionId;
              }
            } catch {
              // URL 中的会话无效时回退到列表首项
            }
          }
        }

        setSessionList(mapped);
        selectSession(targetId, { replace: true });

        const detailRes = await getSession(targetId, {
          userId: DEFAULT_USER_ID,
        });
        if (cancelled) return;

        const detail = detailRes.data;
        if (detail?.session_id) {
          const full = sessionDetailToChatSession(detail);
          setActiveSession(full);
        }
      } catch (error) {
        if (cancelled) return;

        setSessionsError(apiErrorMessage(error, "加载历史会话失败"));
        setSessionList([]);
        setActiveSession(null);
        selectSession("", { replace: true });
      } finally {
        if (!cancelled) {
          setSessionsLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [selectSession]);

  const chatStatus: ChatStatus =
    requestStatus === "ready"
      ? "ready"
      : requestStatus === "error"
        ? "error"
        : requestStatus === "submitted"
          ? "submitted"
          : "streaming";

  const updateActiveSession = useCallback(
    (sessionId: string, updater: (session: ChatSession) => ChatSession) => {
      setActiveSession((session) =>
        session?.id === sessionId ? updater(session) : session,
      );
    },
    [],
  );

  const updateAssistantMessage = useCallback(
    (
      sessionId: string,
      messageId: string,
      updater: (message: ChatMessage) => ChatMessage,
    ) => {
      updateActiveSession(sessionId, (session) => ({
        ...session,
        messages: session.messages.map((message) =>
          message.id === messageId ? updater(message) : message,
        ),
        updatedAt: Date.now(),
      }));
    },
    [updateActiveSession],
  );

  const isCurrentEvent = useCallback(
    (requestId: string, assistantMessageId: string) => {
      const activeRequest = activeRequestRef.current;

      return (
        activeRequest?.requestId === requestId &&
        activeRequest.assistantMessageId === assistantMessageId
      );
    },
    [],
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
      }),
    );
    setRequestStatus("ready");
  }, [updateAssistantMessage]);

  const send = useCallback(
    (text: string) => {
      const value = text.trim();

      if (
        !value ||
        !activeSession ||
        requestStatus !== "ready" ||
        detailLoading
      ) {
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
      const controller = new AbortController();
      const sessionIdAtSend = activeSession.id;
      const isFirstMessage = activeSession.messages.length === 0;
      let resolvedSessionId = sessionIdAtSend;

      const applyOptimisticMessages = (serverSession: ChatSession) => {
        resolvedSessionId = serverSession.id;
        const optimistic: ChatSession = {
          ...serverSession,
          messages: [...serverSession.messages, userMessage, assistantMessage],
          title:
            isFirstMessage || serverSession.title === "新对话"
              ? toTitle(value)
              : serverSession.title,
          updatedAt: now,
        };

        setActiveSession(optimistic);
        setSessionList((prev) => {
          const rest = prev.filter(
            (session) =>
              session.id !== sessionIdAtSend &&
              session.id !== resolvedSessionId,
          );
          return [toSessionListItem(optimistic), ...rest];
        });

        if (resolvedSessionId !== sessionIdAtSend) {
          selectSession(resolvedSessionId, { replace: true });
        }
      };

      const handleStreamEvent = (event: Factors.FactorStreamEvent) => {
        if (!isCurrentEvent(requestId, assistantMessage.id)) {
          return;
        }

        if (event.event === "meta") {
          setRequestStatus("streaming");
          const sources = event.data.sources?.map(sourceItemToChatSource);
          if (sources?.length) {
            updateAssistantMessage(
              resolvedSessionId,
              assistantMessage.id,
              (message) => ({
                ...message,
                sources,
              }),
            );
          }
          return;
        }

        if (event.event === "token") {
          setRequestStatus("streaming");
          updateAssistantMessage(
            resolvedSessionId,
            assistantMessage.id,
            (message) => {
              if (message.status !== "streaming") {
                return message;
              }

              return {
                ...message,
                content: `${message.content}${event.data.content}`,
              };
            },
          );
          return;
        }

        if (event.event === "done") {
          activeRequestRef.current = null;
          setActiveRequestSessionId(null);
          setRequestStatus("ready");
          updateAssistantMessage(
            resolvedSessionId,
            assistantMessage.id,
            (message) => ({
              ...message,
              content: event.data.reply || message.content,
              status: "ready",
            }),
          );

          void getSession(resolvedSessionId, { userId: DEFAULT_USER_ID })
            .then((response) => {
              const title = stripThinkTags(response.data?.title || "");
              if (!title) return;

              const nextTitle =
                isFirstMessage || activeSession.title === "新对话"
                  ? toTitle(value)
                  : title;

              updateActiveSession(resolvedSessionId, (session) => ({
                ...session,
                title: nextTitle,
                updatedAt: Date.now(),
              }));
              setSessionList((prev) =>
                prev.map((session) =>
                  session.id === resolvedSessionId
                    ? { ...session, title: nextTitle, updatedAt: Date.now() }
                    : session,
                ),
              );
            })
            .catch(() => undefined);

          invalidateSessionListCache();
        }
      };

      setRequestStatus("submitted");

      void (async () => {
        try {
          const serverSession = await ensureServerSession(
            activeSession,
            DEFAULT_USER_ID,
          );
          applyOptimisticMessages(serverSession);

          activeRequestRef.current = {
            assistantMessageId: assistantMessage.id,
            controller,
            requestId,
            sessionId: resolvedSessionId,
          };
          setActiveRequestSessionId(resolvedSessionId);

          await queryFactorStream(
            { query: value, session_id: resolvedSessionId },
            {
              onEvent: handleStreamEvent,
              signal: controller.signal,
              userId: DEFAULT_USER_ID,
            },
          );
        } catch (error: unknown) {
          if (controller.signal.aborted) {
            return;
          }

          if (!isCurrentEvent(requestId, assistantMessage.id)) {
            return;
          }

          activeRequestRef.current = null;
          setActiveRequestSessionId(null);
          setRequestStatus("ready");

          const message = apiErrorMessage(error, "生成失败，请稍后重试");
          toast.error(message);

          updateAssistantMessage(
            resolvedSessionId,
            assistantMessage.id,
            (msg) => ({
              ...msg,
              content: msg.content || message,
              errorMessage: message,
              status: "error",
            }),
          );
        }
      })();
    },
    [
      activeSession,
      detailLoading,
      isCurrentEvent,
      requestStatus,
      selectSession,
      updateAssistantMessage,
      updateActiveSession,
    ],
  );

  const handleSubmit = useCallback(
    (message: PromptInputMessage) => {
      send(message.text);
      setInputValue("");
    },
    [send],
  );

  const createNewSession = useCallback(() => {
    if (creatingSession) {
      return;
    }

    if (activeRequestRef.current) {
      stopGeneration();
    }

    setCreatingSession(true);

    void requestNewSession(DEFAULT_USER_ID)
      .then((session) => {
        setSessionList((prev) => [toSessionListItem(session), ...prev]);
        setActiveSession(session);
        selectSession(session.id);
      })
      .catch((error: unknown) => {
        toast.error(apiErrorMessage(error, "创建会话失败"));
      })
      .finally(() => {
        setCreatingSession(false);
      });
  }, [creatingSession, selectSession, stopGeneration]);

  const switchSession = useCallback(
    (sessionId: string) => {
      if (sessionId === activeSessionId) {
        return;
      }

      if (activeRequestRef.current) {
        stopGeneration();
      }

      selectSession(sessionId);
      void loadSessionDetail(sessionId);
    },
    [activeSessionId, loadSessionDetail, selectSession, stopGeneration],
  );

  const deleteSession = useCallback(
    (sessionId: string) => {
      if (
        activeRequestRef.current?.sessionId === sessionId ||
        deletingSessionId
      ) {
        return;
      }

      const session = sessionList.find((item) => item.id === sessionId);

      if (!session) {
        return;
      }

      if (
        !window.confirm(
          `删除“${getSessionDisplayTitle(session)}”？此操作不会保留该会话。`,
        )
      ) {
        return;
      }

      setDeletingSessionId(sessionId);

      void deleteSessionApi(sessionId, { userId: DEFAULT_USER_ID })
        .then((response) => {
          if (!response.data?.deleted) {
            throw new Error("删除会话失败");
          }

          invalidateSessionListCache();

          const next = sessionList.filter((item) => item.id !== sessionId);

          if (next.length > 0) {
            setSessionList(next);
            if (activeSessionId === sessionId) {
              const nextActiveId = next[0].id;
              selectSession(nextActiveId, { replace: true });
              void loadSessionDetail(nextActiveId);
            }
            return;
          }

          setCreatingSession(true);
          return requestNewSession(DEFAULT_USER_ID)
            .then((fallback) => {
              setSessionList([toSessionListItem(fallback)]);
              setActiveSession(fallback);
              selectSession(fallback.id, { replace: true });
            })
            .catch((error: unknown) => {
              setSessionList([]);
              setActiveSession(null);
              selectSession("", { replace: true });
              toast.error(apiErrorMessage(error, "删除后创建新会话失败"));
            })
            .finally(() => {
              setCreatingSession(false);
            });
        })
        .catch((error: unknown) => {
          toast.error(apiErrorMessage(error, "删除会话失败"));
        })
        .finally(() => {
          setDeletingSessionId(null);
        });
    },
    [
      activeSessionId,
      deletingSessionId,
      loadSessionDetail,
      selectSession,
      sessionList,
    ],
  );

  return (
    <div className="flex h-screen min-h-0 bg-background text-foreground">
      <SessionSidebar
        activeRequestSessionId={activeRequestSessionId}
        activeSessionId={activeSessionId}
        creatingSession={creatingSession}
        deletingSessionId={deletingSessionId}
        onCreateSession={createNewSession}
        onDeleteSession={deleteSession}
        onSwitchSession={switchSession}
        sessions={sessionList}
        sessionsError={sessionsError}
        sessionsLoading={sessionsLoading}
      />

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
            disabled={creatingSession || sessionsLoading}
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
              {sessionsLoading ? (
                <ConversationEmptyState
                  description="正在同步历史会话…"
                  icon={<LeafIcon className="size-8" />}
                  title="环检智枢 · AI 工作台"
                />
              ) : detailLoading ? (
                <ConversationEmptyState
                  description="正在加载会话消息…"
                  icon={<LeafIcon className="size-8" />}
                  title={
                    sessionList.find((session) => session.id === activeSessionId)
                      ?.title ?? "正在加载会话"
                  }
                />
              ) : !activeSession ? (
                <ConversationEmptyState
                  description="请选择或新建对话。"
                  icon={<LeafIcon className="size-8" />}
                  title="环检智枢 · AI 工作台"
                />
              ) : activeSession.messages.length === 0 ? (
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
                    {suggestedQuestions.map((suggestion) => (
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
                        <AssistantMessage
                          message={message}
                          onFollowupClick={send}
                          onSourceSelect={setSelectedSource}
                          suggestionsDisabled={requestStatus !== "ready"}
                        />
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
                disabled={requestStatus !== "ready" || detailLoading}
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
};

export default ChatWorkbench;
