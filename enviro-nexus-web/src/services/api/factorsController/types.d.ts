/** factors 模块类型 */
declare namespace Factors {
  type FactorQueryRequest = {
    query: string;
    session_id: string;
  };

  type FactorQueryData = {
    session_id: string;
    matched: boolean;
    reply: string;
    factor?: string | null;
    matched_alias?: string | null;
    card_id?: string | null;
    sources?: API.SourceItem[];
    warnings?: string[];
  };

  type MethodCardIdentity = {
    factor?: string | null;
  };

  type MethodCardContent = {
    card_id?: string | null;
    identity?: MethodCardIdentity | null;
  };

  type MethodCardData = {
    card?: MethodCardContent | null;
  };

  /** POST /api/v1/factors/query/stream — SSE 事件 */
  type StreamMetaEvent = {
    session_id: string;
    matched: boolean;
    factor?: string | null;
    matched_alias?: string | null;
    card_id?: string | null;
    sources?: API.SourceItem[];
    code: string;
  };

  type StreamTokenEvent = {
    content: string;
  };

  type StreamDoneEvent = {
    session_id: string;
    reply: string;
  };

  type StreamErrorEvent = {
    code: string;
    message: string;
  };

  type FactorStreamEvent =
    | { event: "meta"; data: StreamMetaEvent }
    | { event: "token"; data: StreamTokenEvent }
    | { event: "done"; data: StreamDoneEvent }
    | { event: "error"; data: StreamErrorEvent };
}
