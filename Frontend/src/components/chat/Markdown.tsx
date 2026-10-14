import type { ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";

import { CITE_PROTOCOL, citationNumber, linkCitations } from "@/lib/citations";
import { cn } from "@/lib/utils";

// Le HTML éventuel de la réponse est assaini ; seul le protocole interne `cite:` s'ajoute aux
// protocoles de liens autorisés (http, https, mailto…).
const schema = {
  ...defaultSchema,
  protocols: {
    ...defaultSchema.protocols,
    href: [...(defaultSchema.protocols?.href ?? []), CITE_PROTOCOL.replace(":", "")],
  },
};

interface MarkdownProps {
  content: string;
  className?: string;
  /** Rendu d'un renvoi `[n]` ; par défaut, un badge non interactif. */
  renderCitation?: (number: number) => ReactNode;
}

const DefaultCitation = ({ number }: { number: number }) => (
  <sup className="mx-0.5 rounded bg-primary/10 px-1 text-[0.7em] font-semibold text-primary">[{number}]</sup>
);

const Markdown = ({ content, className, renderCitation }: MarkdownProps) => {
  const components: Components = {
    a: ({ href, children, node: _node, ...props }) => {
      const number = citationNumber(href);
      if (number !== null) return <>{renderCitation ? renderCitation(number) : <DefaultCitation number={number} />}</>;
      return (
        <a href={href} target="_blank" rel="noopener noreferrer nofollow" {...props}>
          {children}
        </a>
      );
    },
    table: ({ children, node: _node, ...props }) => (
      <div className="my-3 overflow-x-auto rounded-lg border border-border">
        <table className="m-0 w-full text-sm" {...props}>
          {children}
        </table>
      </div>
    ),
  };

  return (
    <div
      className={cn(
        "prose prose-sm max-w-none dark:prose-invert",
        "prose-p:my-2 prose-headings:font-oswald prose-headings:font-medium prose-headings:tracking-tight",
        "prose-th:bg-muted/60 prose-th:px-3 prose-th:py-2 prose-td:px-3 prose-td:py-2",
        "prose-pre:bg-muted prose-pre:text-foreground prose-code:before:content-none prose-code:after:content-none",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, schema]]}
        urlTransform={(url) => url}
        components={components}
      >
        {linkCitations(content)}
      </ReactMarkdown>
    </div>
  );
};

export default Markdown;
