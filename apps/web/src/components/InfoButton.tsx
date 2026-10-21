"use client";

import { useEffect, useId, useRef, useState } from "react";
import { info } from "../content/info";

/**
 * The info button: an inline "i" after a term or number that opens a small
 * explainer. Plain language first, technical detail second, source link last.
 * Fully keyboard operable; Escape closes and focus returns to the button.
 */
export function InfoButton({ id }: { id: string }) {
  const entry = info(id);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);
  const popId = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        btnRef.current?.focus();
      }
    };
    const onClick = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  return (
    <span ref={wrapRef} className="relative inline-block align-baseline">
      <button
        ref={btnRef}
        type="button"
        aria-label={`More about ${entry.term}`}
        aria-expanded={open}
        aria-controls={popId}
        onClick={() => setOpen((v) => !v)}
        className="hit-44 ml-1.5 inline-flex h-5 w-5 items-center justify-center rounded-full border border-line text-xs font-serif italic leading-none text-muted transition-colors hover:border-primary hover:text-primary"
      >
        i
      </button>
      {open && (
        <span
          id={popId}
          role="dialog"
          aria-label={entry.term}
          className="absolute left-1/2 z-50 mt-2 block w-80 -translate-x-1/2 rounded-[var(--radius-md)] border border-line bg-surface-raised p-4 text-left shadow-[var(--shadow-md)] max-sm:fixed max-sm:inset-x-4 max-sm:left-auto max-sm:w-auto max-sm:translate-x-0"
        >
          <span className="block text-base font-semibold normal-case tracking-normal text-ink">{entry.term}</span>
          <span className="mt-1 block text-base font-normal normal-case leading-relaxed tracking-normal text-muted">
            {entry.plain}
          </span>
          {entry.technical && (
            <span className="mt-2 block border-t border-line pt-2 text-sm font-normal normal-case leading-relaxed tracking-normal text-muted">
              <span className="font-semibold text-ink">In technical terms: </span>
              {entry.technical}
            </span>
          )}
          {entry.sourceUrl && (
            <a
              href={entry.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 block text-sm font-medium normal-case tracking-normal text-primary underline underline-offset-2"
            >
              Source: {entry.sourceLabel ?? entry.sourceUrl}
            </a>
          )}
        </span>
      )}
    </span>
  );
}
