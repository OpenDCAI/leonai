import { memo } from "react";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import type { PluggableList } from "unified";
import remarkGfm from "remark-gfm";

interface MarkdownContentProps {
  content: string;
}

const remarkPlugins: PluggableList = [remarkGfm];

const markdownComponents: Components = {
  code({ className, children, ...props }) {
    const isInline = !className;
    if (isInline) {
      return (
        <code className="bg-[#f5f5f5] px-1.5 py-0.5 rounded text-[0.88em] border border-[#e5e5e5] text-[#171717]" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
};

export default memo(function MarkdownContent({ content }: MarkdownContentProps) {
  if (!content) return null;
  return (
    <div className="markdown-content text-[13px] leading-[1.55] text-[#404040]">
      <ReactMarkdown
        remarkPlugins={remarkPlugins}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
