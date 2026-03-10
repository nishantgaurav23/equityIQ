"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { streamChat } from "@/lib/api";
import ChatMarkdown from "@/components/ChatMarkdown";
import ChatPriceChart from "@/components/ChatPriceChart";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  ticker?: string;
  /** Tickers to render charts for (set by backend "chart" event) */
  chartTickers?: string[];
  verdictSessionId?: string;
  timestamp: Date;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || isStreaming) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);

    const assistantId = crypto.randomUUID();
    const assistantMsg: Message = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      for await (const event of streamChat({
        message: text,
        session_id: sessionId,
      })) {
        if (event.type === "session" && event.session_id) {
          setSessionId(event.session_id);
        } else if (event.type === "token" && event.content) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + event.content }
                : m,
            ),
          );
        } else if (event.type === "context") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    ticker: event.ticker,
                    verdictSessionId: event.verdict_session_id,
                  }
                : m,
            ),
          );
        } else if (event.type === "chart" && event.tickers?.length) {
          // Backend explicitly tells us to show charts for these tickers
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, chartTickers: event.tickers }
                : m,
            ),
          );
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: "Sorry, something went wrong. Please try again." }
            : m,
        ),
      );
    } finally {
      setIsStreaming(false);
      inputRef.current?.focus();
    }
  }, [input, isStreaming, sessionId]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  /** Get chart tickers for a message — backend sends these via the "chart" event */
  const getChartTickers = (msg: Message): string[] => {
    return msg.chartTickers ?? [];
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-4">
        <h1 className="text-2xl font-extrabold gradient-text tracking-tight">Chat with EquityIQ</h1>
        <p className="text-[13px] text-zinc-400 mt-1 font-light">
          Ask about stocks, compare tickers, or get analysis explanations
        </p>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto glass-dark rounded-xl p-4 mb-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-zinc-500 text-sm">
            <div className="text-center space-y-3">
              <div className="w-12 h-12 mx-auto rounded-full bg-gradient-to-br from-amber-500/20 to-rose-500/20 border border-amber-500/30 flex items-center justify-center">
                <span className="text-xl">EQ</span>
              </div>
              <p className="text-zinc-400 font-medium">Start a conversation</p>
              <div className="space-y-2 text-xs">
                <button
                  onClick={() => setInput("Analyze AAPL")}
                  className="block w-full px-4 py-2 rounded-lg glass border border-zinc-700/50 text-zinc-400 hover:text-amber-400 hover:border-amber-500/30 transition-all"
                >
                  &quot;Analyze AAPL&quot;
                </button>
                <button
                  onClick={() => setInput("Compare TSLA vs RIVN")}
                  className="block w-full px-4 py-2 rounded-lg glass border border-zinc-700/50 text-zinc-400 hover:text-amber-400 hover:border-amber-500/30 transition-all"
                >
                  &quot;Compare TSLA vs RIVN&quot;
                </button>
                <button
                  onClick={() => setInput("What is a PE ratio?")}
                  className="block w-full px-4 py-2 rounded-lg glass border border-zinc-700/50 text-zinc-400 hover:text-amber-400 hover:border-amber-500/30 transition-all"
                >
                  &quot;What is a PE ratio?&quot;
                </button>
              </div>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`rounded-2xl ${
                msg.role === "user"
                  ? "max-w-[70%] px-4 py-3 bg-gradient-to-r from-amber-500/20 to-rose-500/20 border border-amber-500/30 text-white"
                  : "max-w-[90%] w-full px-5 py-4 glass border border-zinc-700/50 text-zinc-200"
              }`}
            >
              {msg.role === "user" ? (
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              ) : (
                <>
                  <ChatMarkdown content={msg.content} />
                  {/* Inline price charts — rendered when backend sends "chart" event */}
                  {!isStreaming &&
                    msg.content.length > 0 &&
                    getChartTickers(msg).map((t) => (
                      <ChatPriceChart key={t} ticker={t} />
                    ))}
                </>
              )}
              {/* Ticker badge and timestamp */}
              <div className="flex items-center justify-between mt-2">
                <div className="flex gap-1.5">
                  {msg.ticker && (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium">
                      {msg.ticker}
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-zinc-600">
                  {msg.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          </div>
        ))}

        {isStreaming && messages[messages.length - 1]?.content === "" && (
          <div className="flex justify-start">
            <div className="glass border border-zinc-700/50 rounded-2xl px-4 py-3">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-amber-400 rounded-full animate-bounce" />
                  <span
                    className="w-2 h-2 bg-amber-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  />
                  <span
                    className="w-2 h-2 bg-amber-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  />
                </div>
                <span className="text-[11px] text-zinc-500">Analyzing...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="glass-dark rounded-xl p-3 border border-zinc-700/50">
        <div className="flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about a stock... (e.g. Analyze AAPL, Compare TSLA vs RIVN)"
            disabled={isStreaming}
            className="flex-1 bg-transparent border-none outline-none text-white placeholder-zinc-500 text-sm"
            aria-label="Chat message input"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isStreaming}
            className="px-5 py-2 rounded-lg bg-gradient-to-r from-amber-500 to-rose-600 text-white text-sm font-medium disabled:opacity-40 hover:opacity-90 transition-opacity"
            aria-label="Send message"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
