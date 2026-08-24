"use client";

import { useEffect, useState } from "react";
import { askAssistant, getBuyerBrief } from "../../lib/api";
import type { AssistantResponse, BuyerBrief } from "../../lib/types";

interface BuyerVoiceBriefingProps {
  buyerId: string;
}

export function BuyerVoiceBriefing({ buyerId }: BuyerVoiceBriefingProps) {
  const [brief, setBrief] = useState<BuyerBrief | null>(null);
  const [loading, setLoading] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Interactive Question State
  const [customQuery, setCustomQuery] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatResponse, setChatResponse] = useState<AssistantResponse | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      setSpeechSupported(true);
    }
  }, []);

  const handleFetchBrief = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getBuyerBrief(buyerId);
      setBrief(res.data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load buyer brief");
    } finally {
      setLoading(false);
    }
  };

  const handleSpeak = (textToSpeak?: string) => {
    if (!speechSupported || typeof window === "undefined") return;

    const content = textToSpeak || chatResponse?.spoken_answer || brief?.spoken_summary || brief?.summary;
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

  const handleAskQuestion = async (queryText: string) => {
    if (!queryText.trim()) return;
    setChatLoading(true);
    setError(null);
    try {
      const res = await askAssistant({ query: queryText, buyer_id: buyerId });
      setChatResponse(res.data);
      if (res.data.spoken_answer) {
        handleSpeak(res.data.spoken_answer);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to query assistant");
    } finally {
      setChatLoading(false);
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
          setCustomQuery(transcript);
          void handleAskQuestion(transcript);
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

  const sampleQuestions = [
    "What is their total overdue balance & days overdue?",
    "When was their last WhatsApp reply or promise?",
    "Why are they classified in this reliability tier?",
    "What is the recommended next action for this buyer?",
  ];

  return (
    <div className="rounded-2xl border border-sky-500/30 bg-gradient-to-br from-sky-950/40 via-panel to-panel p-6 backdrop-blur-md shadow-xl space-y-5">
      {/* Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/20 border border-sky-500/30 text-sky-400 text-lg shadow-inner">
            🎙️
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              Interactive Executive AI & Voice Briefing
              <span className="rounded bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 text-[10px] font-mono font-bold text-sky-400">
                Grounded · Read-Only
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Ask anything about this buyer or listen to live audio briefs with browser Web Speech.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Voice Input Mic */}
          <button
            type="button"
            onClick={handleVoiceListen}
            className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-bold transition-all shadow-md ${
              isListening
                ? "bg-rose-500 text-white border-rose-400 animate-pulse"
                : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700 hover:text-white"
            }`}
            title="Speak Question via Microphone"
          >
            <span>{isListening ? "Listening..." : "🎤 Speak Query"}</span>
          </button>

          {/* Generate Summary */}
          <button
            type="button"
            onClick={handleFetchBrief}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-sky-500/20 hover:opacity-90 disabled:opacity-50"
          >
            <span>{loading ? "Summarizing..." : brief ? "Re-summarize" : "Executive Brief"}</span>
          </button>

          {/* Read Aloud Audio */}
          {brief || chatResponse ? (
            <button
              type="button"
              onClick={() => handleSpeak()}
              className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-bold transition-all shadow-md ${
                isPlaying
                  ? "bg-amber-500 text-slate-950 border-amber-400 animate-pulse"
                  : "border-emerald-500/40 bg-emerald-950/40 text-emerald-300 hover:bg-emerald-900/50"
              }`}
            >
              <span>{isPlaying ? "⏹️ Stop Audio" : "🔊 Read Aloud"}</span>
            </button>
          ) : null}
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300">
          {error}
        </div>
      ) : null}

      {/* Interactive Ask Anything Input */}
      <div className="space-y-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleAskQuestion(customQuery);
          }}
          className="flex items-center gap-2"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={customQuery}
              onChange={(e) => setCustomQuery(e.target.value)}
              placeholder="Ask anything about this buyer (e.g. 'What was their last promise date?')..."
              className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:border-sky-500 focus:outline-none shadow-inner"
            />
            {customQuery ? (
              <button
                type="button"
                onClick={() => setCustomQuery("")}
                className="absolute right-3 top-2.5 text-xs text-slate-400 hover:text-white"
              >
                ✕
              </button>
            ) : null}
          </div>
          <button
            type="submit"
            disabled={chatLoading || !customQuery.trim()}
            className="rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-emerald-500/20 hover:opacity-90 disabled:opacity-50"
          >
            {chatLoading ? "Analyzing..." : "Ask DueBot →"}
          </button>
        </form>

        {/* Quick Sample Questions Chips */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-bold uppercase text-slate-500 mr-1">Quick Inquiries:</span>
          {sampleQuestions.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => {
                setCustomQuery(q);
                void handleAskQuestion(q);
              }}
              className="rounded-lg border border-slate-800 bg-slate-900/90 px-2.5 py-1 text-[11px] text-slate-300 hover:border-sky-500/40 hover:bg-slate-800 hover:text-white transition-all shadow-sm"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Loading Spinners */}
      {chatLoading ? (
        <div className="py-6 text-center space-y-2">
          <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
          <p className="text-xs text-slate-400 font-mono">Querying database facts & synthesizing answer...</p>
        </div>
      ) : null}

      {/* Interactive Answer Box */}
      {chatResponse ? (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-4 space-y-3 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="inline-flex rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2.5 py-0.5 text-[10px] font-extrabold uppercase text-emerald-400">
              {chatResponse.category}
            </span>
            <button
              type="button"
              onClick={() => handleSpeak(chatResponse.spoken_answer)}
              className="text-[11px] font-bold text-emerald-400 hover:underline flex items-center gap-1"
            >
              <span>🔊 Listen</span>
            </button>
          </div>
          <p className="text-xs text-slate-100 leading-relaxed font-medium whitespace-pre-line">
            {chatResponse.answer}
          </p>
          {chatResponse.suggested_action ? (
            <div className="rounded-lg border border-emerald-500/20 bg-slate-900/60 p-2.5 text-xs text-emerald-300 flex items-center gap-2">
              <span className="font-bold">Next Step:</span>
              <span>{chatResponse.suggested_action}</span>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Base Executive Brief Summary Card */}
      {brief && !chatResponse ? (
        <div className="space-y-4 pt-1">
          <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 leading-relaxed font-sans text-xs text-slate-200 shadow-inner">
            <p className="font-medium text-slate-100">{brief.summary}</p>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-amber-500/20 bg-amber-950/20 p-3 text-xs space-y-1">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-amber-400">
                Risk Assessment
              </span>
              <p className="font-medium text-amber-200">{brief.risk_assessment}</p>
            </div>

            <div className="rounded-xl border border-emerald-500/20 bg-emerald-950/20 p-3 text-xs space-y-1">
              <span className="text-[10px] font-extrabold uppercase tracking-wider text-emerald-400">
                Recommended Action
              </span>
              <p className="font-medium text-emerald-200">{brief.recommended_action}</p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default BuyerVoiceBriefing;
