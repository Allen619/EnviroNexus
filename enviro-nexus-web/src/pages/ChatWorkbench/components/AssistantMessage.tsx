import { memo, type AnchorHTMLAttributes } from "react";
import { BookOpenIcon } from "lucide-react";
import { MessageResponse } from "@/components/ai-elements/message";
import {
  Reasoning,
  ReasoningContent,
  ReasoningTrigger,
} from "@/components/ai-elements/reasoning";
import {
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "@/components/ai-elements/sources";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { Badge } from "@/components/ui/badge";
import type { ChatMessage, ChatSource } from "@/lib/chat-stream";

const THINK_OPEN_TAG = "<think>";
const THINK_CLOSE_TAG = "</think>";
const SOURCE_REF_PREFIX = "#source-";
const INLINE_SOURCE_TERMS = [
  "电极法",
  "参比电极",
  "氢离子指示电极",
  "标准缓冲溶液",
  "两点校准",
  "温度补偿",
  "酸度计",
  "pH 电极",
  "采样瓶",
  "样品采集",
  "样品保存",
  "低离子强度",
  "高盐度",
  "高氟",
  "质量控制",
  "有证标准样品",
  "平行样",
  "高锰酸盐指数",
  "林格曼黑度",
  "非甲烷总烃",
];

const splitThinkContent = (content: string) => {
  const lowerContent = content.toLowerCase();
  const openIndex = lowerContent.indexOf(THINK_OPEN_TAG);

  if (openIndex === -1) {
    const maybePartialThink = THINK_OPEN_TAG.startsWith(
      content.trim().toLowerCase(),
    );

    return {
      hasThink: maybePartialThink && content.trim().length > 0,
      isThinking: maybePartialThink && content.trim().length > 0,
      reasoning: "",
      response: maybePartialThink ? "" : content,
    };
  }

  const beforeThink = content.slice(0, openIndex).trim();
  const afterOpen = content.slice(openIndex + THINK_OPEN_TAG.length);
  const afterOpenLower = afterOpen.toLowerCase();
  const closeIndex = afterOpenLower.indexOf(THINK_CLOSE_TAG);

  if (closeIndex === -1) {
    return {
      hasThink: true,
      isThinking: true,
      reasoning: afterOpen.trimStart(),
      response: beforeThink,
    };
  }

  const reasoning = afterOpen.slice(0, closeIndex).trim();
  const afterThink = afterOpen
    .slice(closeIndex + THINK_CLOSE_TAG.length)
    .trimStart();
  const response = [beforeThink, afterThink].filter(Boolean).join("\n\n");

  return {
    hasThink: true,
    isThinking: false,
    reasoning,
    response,
  };
};

const normalizeReferenceText = (text: string) =>
  text.toLowerCase().replace(/\s+/g, "");

const normalizeCitationText = (text: string) =>
  normalizeReferenceText(text)
    .replace(/[，,。；;：:、（）()《》【】[\]\-—_]/g, "")
    .replace(/均为/g, "为");

const cleanSourceSection = (section?: string) =>
  section?.replace(/^\s*[\d一二三四五六七八九十]+[.、\s-]*/, "").trim();

const stripEvidencePrefix = (text: string) =>
  text
    .replace(
      /^(标准规定|规定|适用于|适用|采用|使用|通过|将|对|按|以|可|应|需|需要)/,
      "",
    )
    .trim();

const splitEvidenceClauses = (text?: string) =>
  (text ?? "")
    .split(/[。；;，,]/)
    .map((part) => part.trim())
    .filter((part) => part.length >= 4);

const getEvidenceTerms = (source: ChatSource) => {
  const evidenceText = source.content || source.title;
  const clauses = splitEvidenceClauses(evidenceText);
  const terms = [evidenceText?.trim()];

  for (let index = 0; index < clauses.length - 1; index += 1) {
    terms.push(`${clauses[index]}，${clauses[index + 1]}`);
  }

  for (const clause of clauses) {
    terms.push(clause, stripEvidencePrefix(clause));
  }

  return terms.filter((term): term is string =>
    Boolean(term && term.length >= 4),
  );
};

const getInlineTermsForSource = (
  source: ChatSource,
  index: number,
  includeWeakTerms = false,
) => {
  const sourceText = normalizeReferenceText(
    [source.standardNo, source.section, source.title, source.content]
      .filter(Boolean)
      .join(" "),
  );
  const terms = [...getEvidenceTerms(source)];

  for (const term of INLINE_SOURCE_TERMS) {
    if (sourceText.includes(normalizeReferenceText(term))) {
      terms.push(term);
    }
  }

  if (includeWeakTerms) {
    const sectionTerm = cleanSourceSection(source.section);
    if (sectionTerm) {
      terms.push(sectionTerm);
    }

    if (index === 0) {
      terms.push(source.standardNo);
    }
  }

  return Array.from(
    new Set(
      terms
        .filter((term): term is string => Boolean(term && term.trim()))
        .map((term) => term.trim()),
    ),
  );
};

const findTermInContent = (content: string, term: string) => {
  const lowerContent = content.toLowerCase();
  const lowerTerm = term.toLowerCase();
  const exactIndex = lowerContent.indexOf(lowerTerm);

  if (exactIndex !== -1) {
    return { index: exactIndex, length: term.length };
  }

  if (/\s/.test(term)) {
    const compactTerm = term.replace(/\s+/g, "").toLowerCase();
    const compactIndex = lowerContent.indexOf(compactTerm);

    if (compactIndex !== -1) {
      return { index: compactIndex, length: compactTerm.length };
    }
  }

  return null;
};

type InlineAnnotation = {
  index: number;
  length: number;
  insertAt: number;
  sourceIndex: number;
};

type BoldSegment = {
  index: number;
  length: number;
  insertAt: number;
  text: string;
};

const getBoldSegments = (content: string): BoldSegment[] => {
  const segments: BoldSegment[] = [];
  const boldPattern = /\*\*([^*\n]+?)\*\*/g;
  let match: RegExpExecArray | null;

  while ((match = boldPattern.exec(content))) {
    segments.push({
      index: match.index,
      length: match[0].length,
      insertAt: match.index + match[0].length,
      text: match[1].trim(),
    });
  }

  return segments;
};

const isSectionHeadingSegment = (text: string) =>
  /^(?:\d+|[一二三四五六七八九十]+)[.、]\s*.{2,14}$/.test(text.trim());

const scoreBoldSegmentForSource = (
  segment: BoldSegment,
  source: ChatSource,
) => {
  if (isSectionHeadingSegment(segment.text)) {
    return 0;
  }

  const segmentText = normalizeCitationText(segment.text);
  if (segmentText.length < 2) {
    return 0;
  }

  const sourceText = normalizeCitationText(
    [source.title, source.content].filter(Boolean).join(" "),
  );

  if (sourceText.includes(segmentText)) {
    return 1000 + segmentText.length;
  }

  for (const term of getEvidenceTerms(source)) {
    const termText = normalizeCitationText(term);
    if (!termText) {
      continue;
    }
    if (termText.includes(segmentText) || segmentText.includes(termText)) {
      return 800 + Math.min(segmentText.length, termText.length);
    }
  }

  return 0;
};

const addInlineSourceRefs = (content: string, sources?: ChatSource[]) => {
  if (!sources?.length) {
    return content;
  }

  const annotations: InlineAnnotation[] = [];
  const usedTerms = new Set<string>();
  const boldSegments = getBoldSegments(content);

  const hasOverlap = (index: number, length: number) =>
    annotations.some(
      (annotation) =>
        index < annotation.index + annotation.length &&
        annotation.index < index + length,
    );

  for (const [sourceIndex, source] of sources.entries()) {
    const boldMatch = boldSegments
      .map((segment) => ({
        segment,
        score: scoreBoldSegmentForSource(segment, source),
      }))
      .filter(
        ({ segment, score }) =>
          score > 0 && !hasOverlap(segment.index, segment.length),
      )
      .sort((a, b) => b.score - a.score)[0];

    if (boldMatch) {
      annotations.push({ ...boldMatch.segment, sourceIndex });
      continue;
    }

    for (const term of getInlineTermsForSource(source, sourceIndex)) {
      const normalizedTerm = normalizeReferenceText(term);
      if (usedTerms.has(normalizedTerm)) {
        continue;
      }

      const match = findTermInContent(content, term);
      if (!match) {
        continue;
      }

      if (hasOverlap(match.index, match.length)) {
        continue;
      }

      annotations.push({
        ...match,
        insertAt: match.index + match.length,
        sourceIndex,
      });
      usedTerms.add(normalizedTerm);
      break;
    }
  }

  return annotations
    .sort((a, b) => b.insertAt - a.insertAt)
    .reduce((current, annotation) => {
      const marker = `<sup>[${annotation.sourceIndex + 1}](${SOURCE_REF_PREFIX}${annotation.sourceIndex})</sup>`;
      return `${current.slice(0, annotation.insertAt)}${marker}${current.slice(annotation.insertAt)}`;
    }, content);
};

type AssistantMessageProps = {
  message: ChatMessage;
  onFollowupClick: (text: string) => void;
  onSourceSelect: (source: ChatSource) => void;
  suggestionsDisabled: boolean;
};

const AssistantMessage = ({
  message,
  onFollowupClick,
  onSourceSelect,
  suggestionsDisabled,
}: AssistantMessageProps) => {
  const parts = splitThinkContent(message.content);
  const citedResponse = addInlineSourceRefs(parts.response, message.sources);
  const isReasoningStreaming =
    message.status === "streaming" && parts.hasThink && parts.isThinking;
  const sourceLinkComponents = {
    a: ({
      href,
      children,
      node,
      ...props
    }: AnchorHTMLAttributes<HTMLAnchorElement> & { node?: unknown }) => {
      void node;

      if (href?.startsWith(SOURCE_REF_PREFIX)) {
        const sourceIndex = Number(href.slice(SOURCE_REF_PREFIX.length));
        const source = message.sources?.[sourceIndex];

        return (
          <button
            className="relative top-0.5 mx-1 inline-flex h-4 min-w-4 items-center justify-center rounded-[5px] border bg-muted px-1 align-baseline font-medium text-[10px] text-primary leading-none shadow-none transition-colors hover:bg-primary hover:text-primary-foreground"
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              if (source) {
                onSourceSelect(source);
              }
            }}
            title={
              source ? `${source.standardNo} · ${source.section}` : "查看来源"
            }
            type="button"
          >
            {children}
          </button>
        );
      }

      return (
        <a href={href} {...props}>
          {children}
        </a>
      );
    },
  };

  return (
    <>
      {parts.hasThink && (
        <Reasoning
          className="mb-3"
          isStreaming={isReasoningStreaming}
          defaultOpen={isReasoningStreaming}
        >
          <ReasoningTrigger
            getThinkingMessage={(isStreaming, duration) => {
              if (isStreaming || duration === 0) {
                return <span>思考中...</span>;
              }
              if (duration === undefined) {
                return <span>查看思考过程</span>;
              }
              return <span>已思考 {duration} 秒</span>;
            }}
          />
          <ReasoningContent>
            {parts.reasoning || "正在整理思路..."}
          </ReasoningContent>
        </Reasoning>
      )}
      {parts.response && (
        <MessageResponse components={sourceLinkComponents}>
          {citedResponse}
        </MessageResponse>
      )}
      {message.status === "stopped" && (
        <Badge className="w-fit" variant="outline">
          已停止生成
        </Badge>
      )}
      {message.status === "error" && message.errorMessage && (
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
                    onSourceSelect(source);
                  }}
                  title={source.title}
                >
                  <BookOpenIcon className="size-4 shrink-0" />
                  <span className="min-w-0">
                    <span className="block truncate font-medium">
                      {source.standardNo} · {source.section || "章节未标注"}
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
                disabled={suggestionsDisabled}
                key={followup.id}
                onClick={onFollowupClick}
                suggestion={followup.text}
                variant="secondary"
              />
            ))}
          </Suggestions>
        )}
    </>
  );
};

export default memo(AssistantMessage);
