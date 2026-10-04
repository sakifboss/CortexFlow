"use client";

import { useEffect, useRef, useState } from "react";
import { Pause, Play, Square, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { AudioOverviewContent } from "@/types";
import { cn } from "@/lib/utils";

/**
 * Renders a two-host podcast script and plays it back using the browser's
 * SpeechSynthesis API — no backend audio/TTS dependency, works offline. Two
 * distinct voices are chosen for the hosts when the platform provides them.
 */
export function AudioOverviewRenderer({ content }: { content: AudioOverviewContent }) {
  const turns = content.turns ?? [];
  const [playing, setPlaying] = useState(false);
  const [paused, setPaused] = useState(false);
  const [active, setActive] = useState(-1);
  const [supported, setSupported] = useState(true);
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);
  const cancelRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      setSupported(false);
      return;
    }
    const load = () => {
      voicesRef.current = window.speechSynthesis.getVoices();
    };
    load();
    window.speechSynthesis.onvoiceschanged = load;
    return () => {
      cancelRef.current = true;
      window.speechSynthesis.cancel();
    };
  }, []);

  function pickVoice(speaker: string): SpeechSynthesisVoice | undefined {
    const voices = voicesRef.current.filter((v) => v.lang.startsWith("en"));
    if (voices.length === 0) return undefined;
    // Host A → first voice, Host B → a different one for contrast.
    const isB =
      speaker.trim().toLowerCase() === (content.host_b || "").trim().toLowerCase();
    return isB ? voices[1] ?? voices[0] : voices[0];
  }

  function speakFrom(start: number) {
    if (!("speechSynthesis" in window)) return;
    cancelRef.current = false;
    window.speechSynthesis.cancel();
    setPlaying(true);
    setPaused(false);

    const speakIndex = (i: number) => {
      if (cancelRef.current || i >= turns.length) {
        setPlaying(false);
        setActive(-1);
        return;
      }
      setActive(i);
      const u = new SpeechSynthesisUtterance(turns[i].text);
      const v = pickVoice(turns[i].speaker);
      if (v) u.voice = v;
      u.rate = 1.02;
      u.pitch =
        turns[i].speaker.trim().toLowerCase() ===
        (content.host_b || "").trim().toLowerCase()
          ? 0.92
          : 1.08;
      u.onend = () => speakIndex(i + 1);
      u.onerror = () => speakIndex(i + 1);
      window.speechSynthesis.speak(u);
    };
    speakIndex(start);
  }

  function togglePlay() {
    if (!playing) {
      speakFrom(active >= 0 ? active : 0);
    } else if (paused) {
      window.speechSynthesis.resume();
      setPaused(false);
    } else {
      window.speechSynthesis.pause();
      setPaused(true);
    }
  }

  function stop() {
    cancelRef.current = true;
    window.speechSynthesis.cancel();
    setPlaying(false);
    setPaused(false);
    setActive(-1);
  }

  const mins = content.est_seconds ? Math.round(content.est_seconds / 60) : null;

  return (
    <div className="mx-auto max-w-2xl space-y-4 pb-10">
      {/* Player header */}
      <div className="rounded-2xl border bg-gradient-to-br from-rose-500/10 to-pink-500/10 p-5">
        <div className="flex items-center gap-4">
          <div className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-gradient-to-br from-rose-500 to-pink-600 text-white shadow-lg">
            <Volume2 className="h-6 w-6" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-lg font-bold">{content.title}</h1>
            <p className="text-sm text-muted-foreground">
              {content.host_a} & {content.host_b}
              {mins ? ` · ~${mins} min` : ""} · {turns.length} turns
            </p>
          </div>
        </div>
        {content.description && (
          <p className="mt-3 text-sm text-muted-foreground">{content.description}</p>
        )}

        {supported ? (
          <div className="mt-4 flex items-center gap-2">
            <Button onClick={togglePlay} className="gap-2">
              {!playing || paused ? (
                <>
                  <Play className="h-4 w-4" /> {active >= 0 && paused ? "Resume" : "Play"}
                </>
              ) : (
                <>
                  <Pause className="h-4 w-4" /> Pause
                </>
              )}
            </Button>
            {playing && (
              <Button variant="outline" size="icon" onClick={stop}>
                <Square className="h-4 w-4" />
              </Button>
            )}
          </div>
        ) : (
          <p className="mt-4 text-xs text-muted-foreground">
            Audio playback isn't supported in this browser — read the transcript below.
          </p>
        )}
      </div>

      {/* Transcript */}
      <div className="space-y-3">
        {turns.map((t, i) => {
          const isB =
            t.speaker.trim().toLowerCase() ===
            (content.host_b || "").trim().toLowerCase();
          return (
            <div
              key={i}
              onClick={() => supported && speakFrom(i)}
              className={cn(
                "flex cursor-pointer gap-3 rounded-xl border p-3 transition",
                active === i
                  ? "border-rose-400 bg-rose-500/5 shadow-sm"
                  : "hover:bg-muted/40",
                isB && "flex-row-reverse text-right",
              )}
            >
              <div
                className={cn(
                  "grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-semibold text-white",
                  isB ? "bg-pink-600" : "bg-rose-500",
                )}
              >
                {(t.speaker || "?").slice(0, 1).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-muted-foreground">{t.speaker}</p>
                <p className="text-sm">{t.text}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
