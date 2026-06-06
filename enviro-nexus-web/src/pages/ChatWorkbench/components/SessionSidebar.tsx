import {
  LeafIcon,
  MessageSquareIcon,
  PlusIcon,
  Trash2Icon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ChatSession } from "@/lib/chat-stream";
import { cn } from "@/lib/utils";
import { memo } from "react";

type SessionSidebarProps = {
  activeRequestSessionId: string | null;
  activeSessionId: string | null;
  creatingSession: boolean;
  deletingSessionId: string | null;
  onCreateSession: () => void;
  onDeleteSession: (sessionId: string) => void;
  onSwitchSession: (sessionId: string) => void;
  sessions: ChatSession[];
  sessionsError: string | null;
  sessionsLoading: boolean;
};

const SessionSidebar = ({
  activeRequestSessionId,
  activeSessionId,
  creatingSession,
  deletingSessionId,
  onCreateSession,
  onDeleteSession,
  onSwitchSession,
  sessions,
  sessionsError,
  sessionsLoading,
}: SessionSidebarProps) => {
  return (
    <aside className="hidden w-72 shrink-0 border-r bg-muted/25 p-3 md:flex md:flex-col">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-medium">
          <LeafIcon className="size-4" />
          环检智枢
        </div>
        <Button
          aria-label="新建对话"
          disabled={creatingSession || sessionsLoading}
          onClick={onCreateSession}
          size="icon-sm"
          type="button"
        >
          <PlusIcon className="size-4" />
        </Button>
      </div>

      <div className="mt-4 flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto">
        {sessionsLoading && (
          <p className="px-2 py-2 text-muted-foreground text-xs">
            加载历史会话…
          </p>
        )}
        {!sessionsLoading && sessionsError && (
          <p
            className="px-2 py-2 text-destructive text-xs"
            title={sessionsError}
          >
            历史会话加载失败
          </p>
        )}
        {!sessionsLoading &&
          sessions.map((session) => (
            <div
              className={cn(
                "group flex items-center gap-2 rounded-lg px-2 py-2 text-left text-sm",
                session.id === activeSessionId
                  ? "bg-background shadow-xs"
                  : "hover:bg-background/70",
              )}
              key={session.id}
            >
              <button
                className="flex min-w-0 flex-1 items-center gap-2 text-left"
                onClick={() => onSwitchSession(session.id)}
                type="button"
              >
                <MessageSquareIcon className="size-4 shrink-0 text-muted-foreground" />
                <span className="truncate">{session.title || "新对话"}</span>
              </button>
              <Button
                aria-label="删除对话"
                className="opacity-0 group-hover:opacity-100"
                disabled={
                  activeRequestSessionId === session.id ||
                  deletingSessionId === session.id ||
                  Boolean(deletingSessionId)
                }
                onClick={() => onDeleteSession(session.id)}
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
  );
};

export default memo(SessionSidebar);
