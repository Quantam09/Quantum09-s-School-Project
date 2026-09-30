"use client";

import { useEffect, useRef, useState } from "react";
import { Button, Card, CardBody, ErrorNotice, Input, Spinner } from "@/components/ui";
import { ApiError, apiClient, getToken, type AiChatResponse, type Citation } from "@/lib/api";

type Turn = { role: "user" | "assistant"; content: string; citations?: Citation[] };

const WELCOME: Turn = {
  role: "assistant",
  content:
    "Moien! I am your Luxembourgish practice partner. Ask me anything, or try a phrase like " +
    "\"Wéi geet et?\" — I will answer with simple Luxembourgish and English support.",
};

export default function ChatPage() {
  const [turns, setTurns] = useState<Turn[]>([WELCOME]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [turns]);

  async function send() {
    const message = draft.trim();
    if (!message || busy) return;
    if (!getToken()) {
      setError("Please sign in to chat with the AI.");
      return;
    }
    setBusy(true);
    setError(null);
    setDraft("");
    setTurns((prev) => [...prev, { role: "user", content: message }]);
    try {
      const response: AiChatResponse = await apiClient.aiChat(message, sessionId);
      setSessionId(response.session_id);
      setTurns((prev) => [
        ...prev,
        { role: "assistant", content: response.reply, citations: response.citations },
      ]);
    } catch (err) {
      setTurns((prev) => prev.slice(0, -1)); // remove the optimistic user turn
      setDraft(message);
      setError(
        err instanceof ApiError
          ? err.code === "CHAT_UNAVAILABLE"
            ? err.message
            : err.message
          : "Chat failed. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Conversation practice</h1>
        <p className="mt-1 text-sm text-slate-600">
          Practice Luxembourgish with an AI partner grounded in community-reviewed resources.
        </p>
      </div>

      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900">
        The AI is a practice partner, not a cultural authority. For authoritative guidance,
        consult community teachers or elders.
      </div>

      <Card>
        <div
          ref={threadRef}
          className="max-h-[28rem] min-h-[18rem] space-y-3 overflow-y-auto px-4 py-4"
        >
          {turns.map((turn, i) => (
            <div
              key={i}
              className={turn.role === "user" ? "flex justify-end" : "flex justify-start"}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm ${
                  turn.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-100 text-slate-900"
                }`}
              >
                <p className="whitespace-pre-wrap">{turn.content}</p>
                {turn.citations && turn.citations.length > 0 ? (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {turn.citations.map((citation) => (
                      <span
                        key={citation.chunk_id}
                        title={citation.snippet}
                        className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-indigo-700 ring-1 ring-indigo-200"
                      >
                        [{citation.index}] resource {citation.resource_id.slice(-6)}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          ))}
          {busy ? (
            <div className="flex justify-start">
              <Spinner label="Thinking…" />
            </div>
          ) : null}
        </div>
        <CardBody className="border-t border-slate-100">
          {error ? <ErrorNotice message={error} /> : null}
          <div className="mt-2 flex gap-2">
            <Input
              placeholder="Write in Luxembourgish or English…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
            />
            <Button disabled={busy || !draft.trim()} onClick={send}>
              Send
            </Button>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
