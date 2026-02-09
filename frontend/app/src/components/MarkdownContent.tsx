import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownContentProps {
  content: string;
}

export default function MarkdownContent({ content }: MarkdownContentProps) {
  if (!content) return null;
  return (
    <div className="markdown-content text-sm leading-relaxed text-[#404040]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
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
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
