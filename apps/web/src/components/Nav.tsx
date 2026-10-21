"use client";

import Link from "next/link";
import { useState } from "react";
import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "/#problem", label: "The problem" },
  { href: "/#how", label: "How it works" },
  { href: "/#week", label: "A week" },
  { href: "/#demo", label: "Live baseline" },
  { href: "/#evidence", label: "Evidence" },
  { href: "/#impact", label: "Impact" },
  { href: "/#privacy", label: "Privacy" },
  { href: "/#connect", label: "Your own Bee" },
  { href: "/#alexa", label: "Alexa+" },
  { href: "/#api", label: "API" },
  { href: "/#faq", label: "FAQ" },
];

export function Nav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="site-header sticky top-0 z-40 border-b border-line bg-[color-mix(in_srgb,var(--bg)_85%,transparent)] backdrop-blur">
      <div className="mx-auto flex h-16 max-w-[1120px] items-center justify-between gap-5 px-4 sm:px-6 xl:max-w-[1400px]">
        <Link prefetch={false} href="/" className="flex min-h-11 shrink-0 items-center text-lg font-semibold tracking-tight text-ink">
          Bell<span className="text-[var(--accent)]">wether</span>
        </Link>
        {/*
          Eleven links, the theme control and a call to action. Labels never
          break; the row appears from xl, where it was measured to fit with
          the theme control drawn as three icons, and GitHub joins it only
          at 2xl. Below xl the links live in the Menu.
        */}
        <nav className="hidden items-center gap-x-4 xl:flex 2xl:gap-x-5" aria-label="Main">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className="flex min-h-11 items-center whitespace-nowrap text-sm text-muted transition-colors hover:text-ink">
              {l.label}
            </a>
          ))}
        </nav>
        <div className="ml-auto hidden items-center gap-3 md:flex">
          <ThemeToggle compact />
          <a
            href="https://github.com/usv240/bellwether"
            target="_blank"
            rel="noopener noreferrer"
            className="flex min-h-11 items-center whitespace-nowrap text-sm text-muted transition-colors hover:text-ink xl:hidden 2xl:flex"
          >
            GitHub
          </a>
          <Link prefetch={false}
            href="/app"
            className="press inline-flex min-h-11 items-center whitespace-nowrap rounded-[var(--radius-sm)] bg-[var(--primary)] px-4 text-sm font-medium text-[var(--primary-contrast)] hover:opacity-90"
          >
            See a live baseline
          </Link>
        </div>
        <button
          type="button"
          className="press inline-flex min-h-11 items-center rounded-[var(--radius-sm)] border border-line px-4 text-sm font-medium text-ink xl:hidden"
          aria-expanded={open}
          aria-controls="site-menu"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? "Close" : "Menu"}
        </button>
      </div>
      {open && (
        <div id="site-menu" className="border-t border-line bg-surface px-4 pb-4 pt-2 xl:hidden">
          <nav className="flex flex-col" aria-label="Mobile">
            {LINKS.map((l) => (
              <a key={l.href} href={l.href} onClick={() => setOpen(false)} className="flex min-h-11 items-center text-base text-muted hover:text-ink">
                {l.label}
              </a>
            ))}
            <Link prefetch={false} href="/app" className="flex min-h-11 items-center text-base font-medium text-[var(--primary)]">
              See a live baseline
            </Link>
            <a href="https://github.com/usv240/bellwether" className="flex min-h-11 items-center text-base text-muted hover:text-ink">
              GitHub
            </a>
            <div className="mt-2 flex items-center gap-3 border-t border-line pt-4">
              <span className="text-sm text-muted">Theme</span>
              <ThemeToggle />
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
