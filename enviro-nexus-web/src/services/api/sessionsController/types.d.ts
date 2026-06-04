/** sessions 模块类型 */
declare namespace Sessions {
  type ChatMessage = {
    role: "user" | "assistant" | string;
    content: string;
    sources?: API.SourceItem[];
  };

  type SessionDetailData = {
    session_id: string;
    title: string;
    created_at: string;
    updated_at: string;
    messages?: ChatMessage[];
  };

  type SessionSummary = {
    session_id: string;
    title: string;
    created_at: string;
    updated_at: string;
    preview?: string;
    message_count?: number;
  };

  type SessionListData = {
    items: SessionSummary[];
    total: number;
    page: number;
    page_size: number;
  };

  type SessionDeleteData = {
    deleted: boolean;
  };

  type ListSessionsParams = {
    page?: number;
    page_size?: number;
  };
}
