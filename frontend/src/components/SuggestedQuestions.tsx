"use client";

import { Sparkles } from "lucide-react";

export const SUGGESTED_QUESTIONS = [
  "What are the eligibility criteria for campus placements?",
  "What CGPA is required to participate?",
  "Can students attend multiple company drives?",
  "What happens after accepting a placement offer?",
  "What are the rules for internship offers?",
  "What happens if a student rejects an offer?",
];

interface Props {
  onSelect: (question: string) => void;
  disabled?: boolean;
  exclude?: string[];
  title?: string;
  limit?: number;
}

export default function SuggestedQuestions({
  onSelect,
  disabled,
  exclude = [],
  title = "Try asking",
  limit = SUGGESTED_QUESTIONS.length,
}: Props) {
  const items = SUGGESTED_QUESTIONS.filter((q) => !exclude.includes(q)).slice(0, limit);
  if (items.length === 0) return null;

  return (
    <section aria-label={title}>
      <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted">
        <Sparkles className="h-3.5 w-3.5 text-accent" aria-hidden /> {title}
      </h3>
      <ul className="flex flex-wrap gap-2">
        {items.map((q) => (
          <li key={q}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSelect(q)}
              className="rounded-full border border-line bg-surface px-3.5 py-1.5 text-left text-sm text-ink-soft transition hover:border-accent hover:bg-accent-soft hover:text-accent-strong disabled:cursor-not-allowed disabled:opacity-50"
            >
              {q}
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-xs text-muted">
        Example questions only — answers come from the policy documents indexed on the server.
      </p>
    </section>
  );
}
