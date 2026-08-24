"use client";

import { useEffect, useState } from "react";
import { askAssistant } from "../../lib/api";
import type { AssistantResponse } from "../../lib/types";

export function GlobalVoiceAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AssistantResponse | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      setSpeechSupported(true);
    }
  }, []);

  const handleSpeak = (textToSpeak?: string) => {
    if (!speechSupported || typeof window === "undefined") return;
    const content = textToSpeak || response?.spoken_answer || response?.answer;
    if (!content) return;

    window.speechSynthesis.cancel();
    if (isPlaying) {
      setIsPlaying(false);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(content);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(
      (v) => v.lang.includes("en-IN") || v.lang.includes("en-GB") || v.lang.includes("en-US")
    );
    if (preferred) utterance.voice = preferred;

    utterance.onstart = () => setIsPlaying(true);
    utterance.onend = () => setIsPlaying(false);
    utterance.onerror = () => setIsPlaying(false);

    window.speechSynthesis.speak(utterance);
  };

  const handleAsk = async (queryText: string) => {
    if (!queryText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await askAssistant({ query: queryText });
      setResponse(res.data);
      if (res.data.spoken_answer) {
        handleSpeak(res.data.spoken_answer);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to query assistant");
    } finally {
      setLoading(false);
    }
  };

  const handleVoiceListen = () => {
    if (typeof window === "undefined") return;

    const windowWithSpeech = window as unknown as {
      webkitSpeechRecognition?: new () => {
        continuous: boolean;
        lang: string;
        start: () => void;
        onresult: (e: { results?: Array<Array<{ transcript: string }>> }) => void;
        onerror: () => void;
        onend: () => void;
      };
    };

    const SpeechRec = windowWithSpeech.webkitSpeechRecognition;
    if (!SpeechRec) {
      setError("Speech recognition is not supported in this browser. Please use Chrome/Edge or type your question.");
      return;
    }

    try {
      const recognition = new SpeechRec();
      recognition.continuous = false;
      recognition.lang = "en-IN";

      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript ?? "";
        setIsListening(false);
        if (transcript.trim()) {
          setQuery(transcript);
          void handleAsk(transcript);
        }
      };

      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);

      setIsListening(true);
      recognition.start();
    } catch {
      setIsListening(false);
    }
  };

  const quickQueries = [
    "What is our total amount at risk and aging distribution?",
    "Which buyers are chronic late with open invoices?",
    "Show me recent payment promises made by buyers.",
    "Why was an invoice routed to human review?",
  ];

  return (
    <>
      {/* Floating Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full border border-sky-400/40 bg-gradient-to-r from-sky-500 to-indigo-600 px-4 py-3 text-xs font-extrabold text-white shadow-2xl shadow-sky-500/30 hover:scale-105 transition-all"
        title="Open DueBot Executive Voice Assistant"
      >
        <span className="flex h-3 w-3 items-center justify-center">
          <span className="h-2 w-2 rounded-full bg-white animate-ping" />
        </span>
        <span>🎙️ DueBot AI Voice & Status Assistant</span>
      </button>

      {/* Assistant Modal Dialog */}
      {isOpen ? (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-slate-950/80 p-4 backdrop-blur-md animate-in fade-in duration-200">
          <div className="w-full max-w-2xl rounded-3xl border border-sky-500/30 bg-gradient-to-br from-slate-900 via-panel to-slate-950 p-6 shadow-2xl space-y-5">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-sky-500/20 border border-sky-500/30 text-sky-400 text-xl shadow-inner">
                  🎙️
                </div>
                <div>
                  <h3 className="text-base font-extrabold text-white flex items-center gap-2">
                    DueBot Executive Assistant
                    <span className="rounded bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 text-[10px] font-mono font-bold text-sky-400">
                      Live DB Grounded
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Ask anything about any buyer, invoice, aging bucket, promise, or state transition.
                  </p>
                </div>
              </div>

              <button
                type="button"
                onClick={() => {
                  window.speechSynthesis.cancel();
                  setIsPlaying(false);
                  setIsOpen(false);
                }}
                className="rounded-full p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                ✕
              </button>
            </div>

            {/* Error banner */}
            {error ? (
              <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300">
                {error}
              </div>
            ) : null}

            {/* Input & Mic Row */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void handleAsk(query);
              }}
              className="flex items-center gap-2"
            >
              <div className="relative flex-1">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask anything (e.g. 'What is Sen PLC's overdue balance?')..."
                  className="w-full rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none shadow-inner"
                />
              </div>

              {/* Mic Input */}
              <button
                type="button"
                onClick={handleVoiceListen}
                className={`flex items-center justify-center h-10 w-10 rounded-2xl border transition-all shadow-md ${
                  isListening
                    ? "bg-rose-500 text-white border-rose-400 animate-pulse"
                    : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700 hover:text-white"
                }`}
                title="Speak question via microphone"
              >
                🎤
              </button>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="rounded-2xl bg-gradient-to-r from-sky-500 to-indigo-600 px-5 py-3 text-xs font-bold text-white shadow-lg shadow-sky-500/20 hover:opacity-90 disabled:opacity-50"
              >
                {loading ? "Searching..." : "Ask"}
              </button>
            </form>

            {/* Quick Chips */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] font-bold uppercase text-slate-500 mr-1">Quick Inquiries:</span>
              {quickQueries.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => {
                    setQuery(q);
                    void handleAsk(q);
                  }}
                  className="rounded-lg border border-slate-800 bg-slate-900/90 px-2.5 py-1 text-[11px] text-slate-300 hover:border-sky-500/40 hover:bg-slate-800 hover:text-white transition-all shadow-sm"
                >
                  {q}
                </button>
              ))}
            </div>

            {/* Loading */}
            {loading ? (
              <div className="py-8 text-center space-y-2">
                <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
                <p className="text-xs text-slate-400 font-mono">Retrieving live portfolio records & synthesizing response...</p>
              </div>
            ) : null}

            {/* Result Display */}
            {response ? (
              <div className="rounded-2xl border border-sky-500/30 bg-slate-950/80 p-5 space-y-3 shadow-inner">
                <div className="flex items-center justify-between">
                  <span className="inline-flex rounded-full bg-sky-500/10 border border-sky-500/30 px-3 py-0.5 text-[10px] font-extrabold uppercase text-sky-400">
                    {response.category}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleSpeak()}
                    className={`flex items-center gap-1.5 rounded-xl border px-3 py-1 text-xs font-bold transition-all ${
                      isPlaying
                        ? "bg-amber-500 text-slate-950 border-amber-400 animate-pulse"
                        : "border-emerald-500/30 bg-emerald-950/30 text-emerald-300 hover:bg-emerald-900/50"
                    }`}
                  >
                    <span>{isPlaying ? "⏹️ Stop Voice" : "🔊 Read Aloud"}</span>
                  </button>
                </div>

                <div className="text-xs text-slate-100 leading-relaxed font-sans whitespace-pre-line">
                  {response.answer}
                </div>

                {response.suggested_action ? (
                  <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-3 text-xs text-emerald-300 flex items-center gap-2">
                    <span className="font-bold">Recommended Action:</span>
                    <span>{response.suggested_action}</span>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}

export default GlobalVoiceAssistant;
