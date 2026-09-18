/**
 * The Bellwether service. NEXT_PUBLIC_API_URL at build time; the deployed
 * function URL as the fallback so a plain `next build` still points at
 * something real.
 */

export const API =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws";

export const PROFILE = "alex-drift";

export type Tier = "learning" | "stable" | "watch" | "discuss" | "excluded";

export interface Summary {
  profile_id: string;
  simulated: boolean;
  tier: Tier;
  since: string | null;
  latest_date: string | null;
  eligible_days: number;
  excluded_days: number;
  in_warmup: boolean;
  warmup_days_remaining: number;
  stable_streak_days: number;
  contributors: string[];
  explanation: string[];
  disclaimer: string;
}

export interface FeatureAssessment {
  name: string;
  value: number;
  baseline_mean: number | null;
  baseline_sd: number | null;
  z: number | null;
  concern_z: number | null;
  cusum: number;
  tripped: boolean;
  direction: string;
}

export interface Assessment {
  date: string;
  eligible: boolean;
  reason: string | null;
  tier: Tier;
  composite: number | null;
  composite_cusum: number | null;
  features: FeatureAssessment[];
  contributors: string[];
  explanation: string[];
  annotation: string | null;
}

export interface Note {
  text: string;
  source: "bedrock" | "template";
  model: string | null;
  attempts: { model: string; ok: boolean; reason?: string }[];
  facts_text: string;
  simulated: boolean;
}

export interface Report {
  available: boolean;
  simulated?: boolean;
  range?: { from: string; to: string; weeks: number };
  current?: Summary;
  tier_history?: { tier: Tier; from: string; to: string; days: number }[];
  notable_changes?: {
    date: string;
    tier: Tier;
    days: number;
    features: { feature: string; plain: string; direction: string }[];
    explanation: string[];
  }[];
  most_moved_features?: { feature: string; plain: string; mean_concern_z: number }[];
  spoken_checks?: { at: string; kind: string; score: number; detail: string }[];
  annotations?: Record<string, string>;
  eligible_days?: number;
  excluded_days?: number;
  disclaimer: string;
  method?: string;
  citations?: { claim: string; source: string }[];
  message?: string;
}

export async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export const TIER_LABEL: Record<Tier, string> = {
  learning: "Learning",
  stable: "Stable",
  watch: "Watch",
  discuss: "Discuss",
  excluded: "Quiet day",
};

export const TIER_CLASS: Record<Tier, string> = {
  learning: "bg-primary-soft text-[var(--primary)]",
  stable: "bg-success-soft text-[var(--success)]",
  watch: "bg-watch-soft text-[var(--watch)]",
  discuss: "bg-discuss-soft text-[var(--discuss)]",
  excluded: "bg-surface text-muted border border-line",
};

export const FEATURE_LABEL: Record<string, string> = {
  mattr: "vocabulary variety",
  mean_utt_len: "sentence length",
  dep_depth_mean: "sentence structure",
  pronoun_noun_ratio: "pronoun reliance",
  filler_rate: "ums and uhs",
  disfluency_rate: "repeats and restarts",
  low_freq_word_rate: "specific words",
  idea_density: "idea density",
  vocab_size_day: "words used that day",
};

/**
 * The engine names its features the way code does: mean_utt_len,
 * dep_depth_mean, low_freq_word_rate. Those names are correct and they
 * are meaningless to the person the product is for, who is reading this
 * because something about their speech was flagged.
 *
 * The chips on the dashboard already used plain names while the sentences
 * beside them said dep_depth_mean, so the same measure appeared twice on
 * one screen under two names, one of which a reader could not decode.
 * This rewrites the engine's own explanation lines into the same plain
 * vocabulary, so the page speaks one language.
 *
 * Done on the client rather than in the API on purpose: the engine's
 * output stays exact and reproducible, and the presentation layer is the
 * one that owes the reader plain words.
 */
export function humaniseExplanation(line: string): string {
  let out = line;
  for (const [key, label] of Object.entries(FEATURE_LABEL)) {
    out = out.replaceAll(key, label);
  }
  return out;
}

export const FEATURE_INFO: Record<string, string> = {
  mattr: "mattr",
  mean_utt_len: "dep-depth",
  dep_depth_mean: "dep-depth",
  pronoun_noun_ratio: "pronoun-noun",
  filler_rate: "filler-rate",
  disfluency_rate: "filler-rate",
  low_freq_word_rate: "low-freq",
  idea_density: "idea-density",
  vocab_size_day: "mattr",
};

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });
}
