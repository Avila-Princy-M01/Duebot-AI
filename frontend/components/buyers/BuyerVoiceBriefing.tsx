"use client";

import { useEffect, useState } from "react";
import { getBuyerBrief } from "../../lib/api";
import type { BuyerBrief } from "../../lib/types";

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

    const content = textToSpeak || brief?.spoken_summary || brief?.summary;
    if (!content) return;

    window.speechSynthesis.cancel();

    if (isPlaying) {
      setIsPlaying(false);
      return;
    }

    const utterance = new SpeechSynthesisUtterance(content);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Pick a preferred natural English voice if available
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

  const handleVoiceListen = () => {
    if (typeof window === "undefined") return;

    const windowWithSpeech = window as unknown as {
      webkitSpeechRecognition?: new () => {
        continuous: boolean;
        lang: string;
        start: () => void;
        onresult: (e: { results: Array<Array<{ transcript: string }>> }) => void;
        onerror: () => void;
        onend: () => void;
      };
    };

    const SpeechRec = windowWithSpeech.webkitSpeechRecognition;
    if (!SpeechRec) {
      setError("Speech recognition is not supported in this browser. Please use Chrome/Edge or click Generate Brief.");
      return;
    }

    try {
      const recognition = new SpeechRec();
      recognition.continuous = false;
      recognition.lang = "en-IN";

      recognition.onresult = (event) => {
        const transcript = event.results?.[0]?.[0]?.transcript ?? "";
        setIsListening(false);
        if (
          transcript.toLowerCase().includes("brief") ||
          transcript.toLowerCase().includes("summary") ||
          transcript.toLowerCase().includes("status") ||
          transcript.toLowerCase().includes("tell me")
        ) {
          void handleFetchBrief().then(() => {
            if (brief?.spoken_summary) handleSpeak(brief.spoken_summary);
          });
        } else {
          void handleFetchBrief();
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

  return (
    <div className="rounded-2xl border border-sky-500/30 bg-gradient-to-br from-sky-950/40 via-panel to-panel p-6 backdrop-blur-md shadow-xl space-y-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between border-b border-slate-800/80 pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/20 border border-sky-500/30 text-sky-400">
            🎙️
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              AI Executive Voice Briefing
              <span className="rounded bg-sky-500/10 border border-sky-500/30 px-2 py-0.5 text-[10px] font-mono font-bold text-sky-400">
                Scoped · Read-Only
              </span>
            </h3>
            <p className="text-xs text-slate-400">
              Deterministic facts summarized on-demand via browser Web Speech audio.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Voice Input Trigger */}
          <button
            type="button"
            onClick={handleVoiceListen}
            className={`flex items-center gap-1.5 rounded-xl border px-3 py-2 text-xs font-bold transition-all shadow-md ${
              isListening
                ? "bg-rose-500 text-white border-rose-400 animate-pulse"
                : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700 hover:text-white"
            }`}
            title="Ask via Microphone"
          >
            <span>{isListening ? "Listening..." : "🎤 Voice Prompt"}</span>
          </button>

          {/* Generate / Refresh Brief Button */}
          <button
            type="button"
            onClick={handleFetchBrief}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-sky-500 to-blue-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-sky-500/20 hover:opacity-90 disabled:opacity-50"
          >
            <span>{loading ? "Summarizing..." : brief ? "Re-generate Brief" : "Generate Brief"}</span>
          </button>

          {/* Text to Speech Readout Button */}
          {brief ? (
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

      {!brief && !loading ? (
        <div className="py-4 text-center">
          <p className="text-xs text-slate-500">
            Click <strong>Generate Brief</strong> or <strong>Voice Prompt</strong> to get an instant AI executive payment briefing.
          </p>
        </div>
      ) : null}

      {loading ? (
        <div className="py-6 text-center space-y-2">
          <div className="inline-block h-6 w-6 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
          <p className="text-xs text-slate-400 font-mono">Synthesizing payment history & audit trail facts...</p>
        </div>
      ) : null}

      {brief ? (
        <div className="space-y-4 pt-1">
          {/* Executive Summary Card */}
          <div className="rounded-xl border border-slate-800/80 bg-slate-950/60 p-4 leading-relaxed font-sans text-xs text-slate-200 shadow-inner">
            <p className="font-medium text-slate-100">{brief.summary}</p>
          </div>

          {/* Structured Guidance Badges */}
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
