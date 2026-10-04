"use client";

import { useState } from "react";
import { Check, RotateCcw, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { QuizContent } from "@/types";
import { cn } from "@/lib/utils";

export function QuizRenderer({ content }: { content: QuizContent }) {
  const questions = content.questions ?? [];
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submitted, setSubmitted] = useState(false);

  if (questions.length === 0) {
    return <p className="text-center text-muted-foreground">No questions generated.</p>;
  }

  const score = questions.reduce(
    (acc, q, i) => acc + (answers[i] === q.answer_index ? 1 : 0),
    0,
  );
  const allAnswered = questions.every((_, i) => answers[i] !== undefined);

  function reset() {
    setAnswers({});
    setSubmitted(false);
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5 pb-10">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">{content.title}</h1>
        {submitted && (
          <div
            className={cn(
              "rounded-full px-3 py-1 text-sm font-semibold",
              score / questions.length >= 0.7
                ? "bg-emerald-500/15 text-emerald-600"
                : score / questions.length >= 0.4
                  ? "bg-amber-500/15 text-amber-600"
                  : "bg-destructive/15 text-destructive",
            )}
          >
            {score} / {questions.length}
          </div>
        )}
      </div>

      {questions.map((q, qi) => {
        const chosen = answers[qi];
        return (
          <div key={qi} className="rounded-xl border p-4">
            <p className="mb-3 font-medium">
              <span className="mr-2 text-muted-foreground">{qi + 1}.</span>
              {q.question}
            </p>
            <div className="space-y-2">
              {q.options.map((opt, oi) => {
                const isChosen = chosen === oi;
                const isCorrect = oi === q.answer_index;
                let state = "idle";
                if (submitted) {
                  if (isCorrect) state = "correct";
                  else if (isChosen) state = "wrong";
                } else if (isChosen) {
                  state = "chosen";
                }
                return (
                  <button
                    key={oi}
                    disabled={submitted}
                    onClick={() => setAnswers((a) => ({ ...a, [qi]: oi }))}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-lg border px-3 py-2 text-left text-sm transition",
                      state === "idle" && "hover:border-primary/40 hover:bg-muted/40",
                      state === "chosen" && "border-primary bg-primary/10",
                      state === "correct" && "border-emerald-500 bg-emerald-500/10",
                      state === "wrong" && "border-destructive bg-destructive/10",
                    )}
                  >
                    <span
                      className={cn(
                        "grid h-5 w-5 shrink-0 place-items-center rounded-full border text-xs font-semibold",
                        state === "correct" && "border-emerald-500 bg-emerald-500 text-white",
                        state === "wrong" && "border-destructive bg-destructive text-white",
                      )}
                    >
                      {submitted && isCorrect ? (
                        <Check className="h-3 w-3" />
                      ) : submitted && isChosen ? (
                        <X className="h-3 w-3" />
                      ) : (
                        String.fromCharCode(65 + oi)
                      )}
                    </span>
                    <span>{opt}</span>
                  </button>
                );
              })}
            </div>
            {submitted && q.explanation && (
              <p className="mt-3 rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
                <span className="font-semibold text-foreground">Why: </span>
                {q.explanation}
              </p>
            )}
          </div>
        );
      })}

      <div className="flex justify-end gap-2">
        {submitted ? (
          <Button variant="outline" onClick={reset}>
            <RotateCcw className="h-4 w-4" /> Retry
          </Button>
        ) : (
          <Button onClick={() => setSubmitted(true)} disabled={!allAnswered}>
            Submit {allAnswered ? "" : `(${Object.keys(answers).length}/${questions.length})`}
          </Button>
        )}
      </div>
    </div>
  );
}
