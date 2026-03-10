"use client";

import React, { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

/**
 * Detect whether a text token looks like a positive, negative, or neutral financial value.
 * Returns a colored <span> or the original string.
 */
function colorizeFinancialValue(text: string): React.ReactNode {
  // Split text into segments, colorizing financial values inline
  const parts: React.ReactNode[] = [];
  // Match patterns like: +0.35, -24.2%, $219.27, 84%, 337.86, 0.17%, -5.09%, Beta 2.08
  const pattern =
    /([+-]?\$?\d+(?:,\d{3})*(?:\.\d+)?%?(?:\s*[BMK])?)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    // Push text before this match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const val = match[1];
    const numericStr = val.replace(/[$%,BMK\s]/g, "");
    const num = parseFloat(numericStr);

    let colorClass = "text-zinc-300"; // neutral
    if (!isNaN(num)) {
      if (val.startsWith("+") || val.startsWith("$")) {
        // Explicit positive prefix
        colorClass = num > 0 ? "text-emerald-400" : num < 0 ? "text-red-400" : "text-zinc-300";
      } else if (val.startsWith("-")) {
        colorClass = "text-red-400";
      } else if (val.includes("%")) {
        // Percentages: context-dependent but color large/notable ones
        // Don't color generic percentages that aren't clearly good/bad
        colorClass = "text-amber-300 font-medium";
      } else {
        // Plain number, keep neutral
        colorClass = "text-zinc-200 font-medium";
      }
    }

    parts.push(
      <span key={match.index} className={colorClass}>
        {val}
      </span>,
    );
    lastIndex = match.index + val.length;
  }

  if (parts.length === 0) return text;
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return <>{parts}</>;
}

/** Colorize signal keywords like BUY, SELL, HOLD, STRONG_BUY, etc. */
function colorizeSignals(text: string): React.ReactNode {
  const signalPattern =
    /\b(STRONG[_ ]BUY|STRONG[_ ]SELL|BUY|SELL|HOLD|BULLISH|BEARISH|NEUTRAL)\b/gi;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = signalPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const signal = match[1].toUpperCase().replace(" ", "_");
    let cls = "text-zinc-300";
    if (signal.includes("BUY") || signal === "BULLISH") cls = "text-emerald-400 font-semibold";
    else if (signal.includes("SELL") || signal === "BEARISH") cls = "text-red-400 font-semibold";
    else if (signal === "HOLD" || signal === "NEUTRAL") cls = "text-amber-400 font-semibold";

    parts.push(
      <span key={match.index} className={cls}>
        {match[1]}
      </span>,
    );
    lastIndex = match.index + match[1].length;
  }

  if (parts.length === 0) return text;
  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return <>{parts}</>;
}

/** Apply both signal and financial value colorization */
function colorizeText(text: string): React.ReactNode {
  // First pass: colorize signals, producing an array of strings and React nodes
  const signalResult = colorizeSignals(text);
  if (typeof signalResult === "string") {
    return colorizeFinancialValue(signalResult);
  }
  // If signals were found, we need to further process the string segments
  const element = signalResult as React.ReactElement<{ children?: React.ReactNode }>;
  const children = React.Children.toArray(element.props.children);
  return (
    <>
      {children.map((child, i) =>
        typeof child === "string" ? (
          <React.Fragment key={i}>{colorizeFinancialValue(child)}</React.Fragment>
        ) : (
          child
        ),
      )}
    </>
  );
}

/** Risk-level badge */
function RiskBadge({ level }: { level: string }) {
  const upper = level.toUpperCase();
  let cls = "bg-amber-500/15 text-amber-400 border-amber-500/30";
  if (upper === "HIGH" || upper === "VERY HIGH")
    cls = "bg-red-500/15 text-red-400 border-red-500/30";
  else if (upper === "LOW") cls = "bg-emerald-500/15 text-emerald-400 border-emerald-500/30";

  return (
    <span
      className={`inline-block px-2 py-0.5 text-[11px] font-semibold rounded-md border ${cls}`}
    >
      {level}
    </span>
  );
}

/** Custom markdown components for professional financial output */
function useMarkdownComponents(): Components {
  return useMemo<Components>(
    () => ({
      // Headings — different sizes with accent color
      h1: ({ children }) => (
        <h1 className="text-xl font-bold text-amber-400 mt-5 mb-2 pb-1 border-b border-zinc-700/50">
          {children}
        </h1>
      ),
      h2: ({ children }) => (
        <h2 className="text-lg font-bold text-amber-400/90 mt-4 mb-2">
          {children}
        </h2>
      ),
      h3: ({ children }) => (
        <h3 className="text-base font-semibold text-zinc-100 mt-3 mb-1.5">
          {children}
        </h3>
      ),
      h4: ({ children }) => (
        <h4 className="text-sm font-semibold text-zinc-200 mt-2 mb-1">
          {children}
        </h4>
      ),

      // Paragraphs with financial value colorization
      p: ({ children }) => {
        const processed = React.Children.map(children, (child) => {
          if (typeof child === "string") return colorizeText(child);
          return child;
        });
        return <p className="text-[13px] leading-relaxed text-zinc-300 my-1.5">{processed}</p>;
      },

      // Strong/Bold
      strong: ({ children }) => {
        // Check if the content is a signal keyword
        const text = typeof children === "string" ? children : "";
        const upper = text.toUpperCase().replace(/\s+/g, "_");
        if (["BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL"].includes(upper)) {
          let cls = "text-amber-400";
          if (upper.includes("BUY")) cls = "text-emerald-400";
          else if (upper.includes("SELL")) cls = "text-red-400";
          return <strong className={`font-bold ${cls}`}>{children}</strong>;
        }
        // Check for risk levels
        if (["HIGH", "MEDIUM", "LOW", "VERY HIGH"].includes(upper)) {
          return (
            <strong className="font-bold">
              <RiskBadge level={text} />
            </strong>
          );
        }
        return <strong className="font-semibold text-zinc-100">{children}</strong>;
      },

      // Lists with proper indentation
      ul: ({ children }) => (
        <ul className="space-y-1 my-2 ml-1">{children}</ul>
      ),
      ol: ({ children }) => (
        <ol className="space-y-1 my-2 ml-1 list-decimal list-inside">{children}</ol>
      ),
      li: ({ children }) => {
        const processed = React.Children.map(children, (child) => {
          if (typeof child === "string") return colorizeText(child);
          return child;
        });
        return (
          <li className="text-[13px] text-zinc-300 leading-relaxed pl-2 relative before:content-[''] before:absolute before:left-0 before:top-[9px] before:w-1 before:h-1 before:bg-amber-500/60 before:rounded-full">
            <span className="ml-2">{processed}</span>
          </li>
        );
      },

      // Tables — styled for dark theme with proper spacing
      table: ({ children }) => (
        <div className="my-3 overflow-x-auto rounded-lg border border-zinc-700/50">
          <table className="w-full text-[12px]">{children}</table>
        </div>
      ),
      thead: ({ children }) => (
        <thead className="bg-zinc-800/60 border-b border-zinc-700/50">{children}</thead>
      ),
      tbody: ({ children }) => <tbody className="divide-y divide-zinc-800/50">{children}</tbody>,
      tr: ({ children }) => (
        <tr className="hover:bg-zinc-800/30 transition-colors">{children}</tr>
      ),
      th: ({ children }) => (
        <th className="px-3 py-2 text-left text-[11px] font-semibold text-amber-400/80 uppercase tracking-wider whitespace-nowrap">
          {children}
        </th>
      ),
      td: ({ children }) => {
        const processed = React.Children.map(children, (child) => {
          if (typeof child === "string") return colorizeText(child);
          return child;
        });
        return (
          <td className="px-3 py-2 text-zinc-300 whitespace-nowrap">{processed}</td>
        );
      },

      // Code blocks
      code: ({ className, children, ...rest }) => {
        const isInline = !className;
        if (isInline) {
          return (
            <code className="bg-zinc-800/60 text-amber-300 px-1.5 py-0.5 rounded text-[12px] font-mono">
              {children}
            </code>
          );
        }
        return (
          <code
            className={`block bg-zinc-900/60 rounded-lg p-3 text-[12px] font-mono text-zinc-300 overflow-x-auto my-2 ${className}`}
            {...rest}
          >
            {children}
          </code>
        );
      },
      pre: ({ children }) => <pre className="my-2">{children}</pre>,

      // Blockquotes
      blockquote: ({ children }) => (
        <blockquote className="border-l-2 border-amber-500/40 pl-3 my-2 text-zinc-400 italic">
          {children}
        </blockquote>
      ),

      // Horizontal rule
      hr: () => <hr className="border-zinc-700/50 my-3" />,

      // Links
      a: ({ href, children }) => (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-amber-400 hover:text-amber-300 underline underline-offset-2"
        >
          {children}
        </a>
      ),
    }),
    [],
  );
}

interface ChatMarkdownProps {
  content: string;
}

export default function ChatMarkdown({ content }: ChatMarkdownProps) {
  const components = useMarkdownComponents();

  return (
    <div className="chat-markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
