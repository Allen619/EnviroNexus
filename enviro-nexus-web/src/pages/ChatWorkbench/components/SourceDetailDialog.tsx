import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { ChatSource } from "@/lib/chat-stream";
import { memo } from "react";

const formatRelevance = (value: number) => `${Math.round(value * 100)}%`;

type SourceDetailDialogProps = {
  onOpenChange: (open: boolean) => void;
  source: ChatSource | null;
};

const SourceDetailDialog = ({
  onOpenChange,
  source,
}: SourceDetailDialogProps) => {
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
};

export default memo(SourceDetailDialog);
