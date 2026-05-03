"use client";

import { useState, useRef, useEffect } from "react";
import api from "@/lib/api";
import { useChatStore, type Message } from "@/store/chat";

interface ChatProps {
  onTimetableGenerated?: (timetableId: string) => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Chat({ onTimetableGenerated }: ChatProps) {
  const {
    messages,
    sessionId,
    addMessage,
    updateLastMessage,
    replaceLastMessageError,
  } = useChatStore();

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    addMessage({ role: "user", content: text });
    setInput("");
    setLoading(true);

    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    addMessage({ role: "assistant", content: "" });

    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          history,
        }),
      });

      if (!response.ok || !response.body) {
        throw new Error("Failed to connect to chat API");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullContent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (data === "[DONE]") break;
          try {
            const parsed = JSON.parse(data);
            if (parsed.content) {
              fullContent += parsed.content;
              updateLastMessage(fullContent);

              // Check if a timetable was generated
              const match = fullContent.match(
                /timetable\s+id[:]\s*([a-f0-9-]{36})/i
              );
              if (match && onTimetableGenerated) {
                onTimetableGenerated(match[1]);
              }
            }
            if (parsed.error) {
              fullContent += `\n⚠️ Error: ${parsed.error}`;
              updateLastMessage(fullContent);
            }
          } catch {
            // skip malformed JSON
          }
        }
      }
    } catch (err: unknown) {
      const errMsg =
        (err as Error)?.message ?? "An error occurred. Please try again.";
      replaceLastMessageError(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full" style={{ height: "calc(100vh - 64px)" }}>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} />
        ))}
        {loading && messages[messages.length - 1]?.content === "" && (
          <div className="flex items-center gap-2 text-gray-400">
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
            <span className="text-sm">Thinking…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="border-t bg-white px-4 py-4">
        <div className="flex gap-2 max-w-4xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me to add faculty, generate timetable, check conflicts…"
            rows={2}
            className="flex-1 resize-none border rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-5 py-3 bg-primary text-white rounded-xl font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-gray-400 text-center mt-2">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-3xl rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? "bg-primary text-white rounded-tr-sm"
            : "bg-white border shadow-sm rounded-tl-sm text-gray-800"
        }`}
      >
        <MarkdownContent content={message.content} />
      </div>
    </div>
  );
}

function MarkdownContent({ content }: { content: string }) {
  // Simple markdown renderer for tables and bold text
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let tableRows: string[][] = [];
  let inTable = false;
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (line.trim().startsWith("|")) {
      inTable = true;
      const cells = line
        .split("|")
        .slice(1, -1)
        .map((c) => c.trim());
      // Skip separator rows like |---|---|
      if (!cells.every((c) => /^[-: ]+$/.test(c))) {
        tableRows.push(cells);
      }
    } else {
      if (inTable && tableRows.length > 0) {
        elements.push(
          <div key={i} className="overflow-x-auto my-2">
            <table className="text-xs border-collapse w-full">
              <thead>
                <tr>
                  {tableRows[0].map((h, j) => (
                    <th
                      key={j}
                      className="bg-primary text-white px-3 py-1.5 border border-blue-400 text-left"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tableRows.slice(1).map((row, ri) => (
                  <tr
                    key={ri}
                    className={ri % 2 === 0 ? "bg-white" : "bg-blue-50"}
                  >
                    {row.map((cell, ci) => (
                      <td
                        key={ci}
                        className="px-3 py-1.5 border border-gray-200"
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        tableRows = [];
        inTable = false;
      }
      if (line.trim()) {
        elements.push(
          <p key={i} className="mb-1 whitespace-pre-wrap">
            {formatInline(line)}
          </p>
        );
      } else {
        elements.push(<br key={i} />);
      }
    }
    i++;
  }

  // Flush remaining table
  if (inTable && tableRows.length > 0) {
    elements.push(
      <div key="table-final" className="overflow-x-auto my-2">
        <table className="text-xs border-collapse w-full">
          <thead>
            <tr>
              {tableRows[0].map((h, j) => (
                <th
                  key={j}
                  className="bg-primary text-white px-3 py-1.5 border border-blue-400 text-left"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableRows.slice(1).map((row, ri) => (
              <tr key={ri} className={ri % 2 === 0 ? "bg-white" : "bg-blue-50"}>
                {row.map((cell, ci) => (
                  <td key={ci} className="px-3 py-1.5 border border-gray-200">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return <>{elements}</>;
}

function formatInline(text: string): React.ReactNode {
  // Bold **text**
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}
