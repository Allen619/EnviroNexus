/**
 * 公共类型（与 enviro-nexus-api OpenAPI 对齐）
 * @see http://localhost:8080/docs
 */
declare namespace API {
  /** 统一成功响应外壳 */
  type ApiResponse<T> = {
    success: boolean;
    code: string;
    message: string;
    api_version?: string;
    request_id?: string | null;
    data?: T | null;
    error?: ErrorDetail | null;
    timestamp: string;
  };

  /** 4xx / 5xx 错误响应 */
  type ErrorResponse = {
    success?: boolean;
    code: string;
    message: string;
    api_version?: string;
    request_id?: string | null;
    data?: null;
    error?: ErrorDetail | null;
    timestamp: string;
  };

  type ErrorDetail = {
    details?: Record<string, unknown>[] | null;
  };

  /** 知识库引用（sessions 消息与 factors 查询共用） */
  type SourceItem = {
    evidence_id?: string | null;
    source_title?: string;
    section?: string;
    summary?: string;
    field_path?: string | null;
  };
}
