"use client";

import Link from "next/link";
import { useState } from "react";
import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "/#problem", label: "The problem" },
  { href: "/#how", label: "How it works" },
  { href: "/#demo", label: "Live baseline" },
  { href: "/#evidence", label: "Evidence" },
  { href: "/#privacy", label: "Privacy" },
  { href: "/#connect", label: "Your own Bee" },
  { href: "/#alexa", label: "Alexa+" },
  { href: "/#api", label: "API" },
  { href: "/#faq", label: "FAQ" },
];

export function Nav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-[color-mix(in_srgb,var(--bg)_85%,transparent)] backdrop-blur">
      <div className="mx-auto flex h-16 max-w-[1120px] items-center justify-between px-4 sm:px-6">
        <Link prefetch={false} href="/" className="text-lg font-semibold tracking-tight text-ink">
          Bell<span className="text-[var(--accent)]">wether</span>
        </Link>
        {/*
          Nine links, a theme toggle, GitHub and a call to action do not
          fit on one line below about 1280px, and with md:flex they tried
          anyway: every two-word label broke onto two lines. Adding one
          more link ("Your own Bee") took it from one wrapped label to
          five, and a ninth ("Alexa+") was measured rather than
          guessed at before it went in. So labels never break, and the full row appears only where
          it fits; below that the links live in the Menu.
        */}
        <nav className="hidden items-center gap-4 xl:flex" aria-label="Main">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="whitespace-nowrap text-sm text-muted transition-colors hover:text-ink">
              {l.label}
            </a>
          ))}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          <ThemeToggle />
          <a
            href="https://github.com/usv240/bellwether"
            target="_blank"
            rel="noopener noreferrer"
            className="whitespace-nowrap text-sm text-muted transition-colors hover:text-ink"
          >
            GitHub
          </a>
          <Link prefetch={false}
            href="/app"
            className="whitespace-nowrap rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--primary-contrast)] transition-opacity hover:opacity-90"
          >
            See a live baseline
          </Link>
        </div>
        <button
          type="button"
          className="rounded-[var(--radius-sm)] border border-line px-3 py-2 text-sm text-ink xl:hidden"
          aria-expanded={open}
          aria-label="Toggle menu"
          onClick={() => setOpen((v) => !v)}
        >
          Menu
        </button>
      </div>
      {open && (
        <div className="border-t border-line bg-surface px-4 py-4 xl:hidden">
          <nav className="flex flex-col gap-3" aria-label="Mobile">
            {LINKS.map((l) => (
              <a key={l.href} href={l.href} onClick={() => setOpen(false)} className="text-sm text-muted">
                {l.label}
              </a>
            ))}
            <Link prefetch={false} href="/app" className="text-sm font-medium text-[var(--primary)]">
              See a live baseline
            </Link>
            <a href="https://github.com/usv240/bellwether" className="text-sm text-muted">
              GitHub
            </a>
            <div className="pt-2">
              <ThemeToggle />
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
