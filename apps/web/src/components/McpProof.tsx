"use client";

import { useState } from "react";
import { API, TIER_LABEL, TIER_CLASS, humaniseExplanation, type Tier } from "../lib/api";

/**
 * The Alexa+ surface, shown working rather than claimed.
 *
 * The Alexa+ track asks for a self-hosted MCP server on spec 2025-11-25
 * over Streamable HTTP, shown in action. Bellwether has one, deployed,
 * with eighteen conformance and behaviour tests, and until this panel a
 * visitor had no way to see it. The word MCP appeared once on the page,
 * in a developer section, next to a URL. That is the position both
 * sibling projects were in before they added a panel like this one:
 * real underneath, invisible above.
 *
 * It matters more here than it did there. The question this product
 * exists to answer is spoken out loud, in a kitchen, by somebody who has
 * been wondering for a while: how have I been sounding lately. Nobody
 * asks that by opening a dashboard. If the spoken surface is the real
 * one, a page that only shows the dashboard is showing the wrong half.
 *
 * One press runs a complete session from this browser against the
 * deployed server, exactly as an assistant would: agree a protocol
 * version, finish the handshake, ask what tools exist, call one, close
 * the session. Every row is the server's own answer.
 *
 * `get_speech_vitals` is the tool it calls because it is the spoken
 * question, and because it reads the same profile the dashboard above
 * shows, which is why the tier it returns can be compared against the
 * page. It reads and never writes. Three of the seven tools do write,
 * and this panel calls none of them.
 */

const MCP_URL = `${API}/mcp`;
const PROTOCOL = "2025-11-25";

interface Step {
  label: string;
  request: string;
  status: number;
  ok: boolean;
  shows: string;
}

interface Vitals {
  tier: Tier;
  simulated: boolean;
  eligible_days: number;
  explanation: string[];
}

async function rpc(body: object, session?: string) {
  const headers: Record<string, string> = {
    "content-type": "application/json",
    accept: "application/json, text/event-stream",
  };
  if (session) {
    headers["mcp-session-id"] = session;
    headers["mcp-protocol-version"] = PROTOCOL;
  }
  const res = await fetch(MCP_URL, { method: "POST", headers, body: JSON.stringify(body) });
  const text = await res.text();
  let json: unknown = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }
  return { status: res.status, session: res.headers.get("mcp-session-id"), json };
}

const short = (id: string) => (id.length > 14 ? `${id.slice(0, 8)}...${id.slice(-4)}` : id);

export function McpProof() {
  const [state, setState] = useState<"idle" | "running" | "done" | "error">("idle");
  const [steps, setSteps] = useState<Step[]>([]);
  const [vitals, setVitals] = useState<Vitals | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ms, setMs] = useState(0);

  const run = async () => {
    setState("running");
    setSteps([]);
    setVitals(null);
    setError(null);
    const started = performance.now();
    const out: Step[] = [];
    const push = (s: Step) => {
      out.push(s);
      setSteps([...out]);
    };

    try {
      const init = await rpc({
        jsonrpc: "2.0",
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: PROTOCOL,
          capabilities: {},
          clientInfo: { name: "bellwether-site", version: "1" },
        },
      });
      const session = init.session;
      const agreed = (init.json as { result?: { protocolVersion?: string } })?.result
        ?.protocolVersion;
      if (!session || agreed !== PROTOCOL) {
        throw new Error(`the server did not open a ${PROTOCOL} session (status ${init.status})`);
      }
      push({
        label: "Agree a protocol and open a session",
        request: "initialize",
        status: init.status,
        ok: true,
        shows: `protocol ${agreed}, session ${short(session)}`,
      });

      const ready = await rpc({ jsonrpc: "2.0", method: "notifications/initialized" }, session);
      push({
        label: "Finish the handshake",
        request: "notifications/initialized",
        status: ready.status,
        ok: ready.status === 202,
        shows: "accepted with no body, as the spec requires of a notification",
      });

      const list = await rpc({ jsonrpc: "2.0", id: 2, method: "tools/list" }, session);
      const tools =
        (list.json as { result?: { tools?: { name: string }[] } })?.result?.tools?.map(
          (t) => t.name,
        ) ?? [];
      push({
        label: "Ask what an assistant can do here",
        request: "tools/list",
        status: list.status,
        ok: tools.length > 0,
        shows: `${tools.length} tools: ${tools.join(", ")}`,
      });

      const call = await rpc(
        {
          jsonrpc: "2.0",
          id: 3,
          method: "tools/call",
          params: { name: "get_speech_vitals", arguments: {} },
        },
        session,
      );
      const text =
        (call.json as { result?: { content?: { text?: string }[] } })?.result?.content?.[0]
          ?.text ?? "";
      let parsed: Vitals | null = null;
      try {
        parsed = JSON.parse(text) as Vitals;
      } catch {
        parsed = null;
      }
      push({
        label: "Ask how this person has been sounding",
        request: "tools/call get_speech_vitals",
        status: call.status,
        ok: parsed !== null,
        shows: parsed
          ? `tier ${TIER_LABEL[parsed.tier] ?? parsed.tier}, over ${parsed.eligible_days} assessed days`
          : "no answer returned",
      });
      setVitals(parsed);

      const end = await fetch(MCP_URL, {
        method: "DELETE",
        headers: { "mcp-session-id": session },
      });
      push({
        label: "Close the session",
        request: "DELETE",
        status: end.status,
        ok: end.status === 200 || end.status === 204,
        shows: "session ended on the server",
      });

      setMs(Math.round(performance.now() - started));
      setState("done");
    } catch (err) {
      // A proof that fails must read as a failure, not as a half-filled
      // table somebody could mistake for success.
      setError((err as Error).message);
      setState("error");
    }
  };

  return (
    <div className="rounded-[var(--radius-lg)] border border-line bg-bg p-6 sm:p-8">
      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-full bg-primary-soft px-3 py-1 text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
          MCP 2025-11-25
        </span>
        <h3 className="text-lg font-semibold tracking-tight">
          Asking out loud, instead of opening a dashboard
        </h3>
      </div>

      <p className="mt-4 max-w-[760px] text-sm leading-relaxed text-muted">
        The question this product answers is one people ask out loud: how
        have I been sounding lately. Bellwether answers it through the
        Model Context Protocol, which is how Alexa+ talks to tools. Press
        this and your browser will hold a complete session with the
        deployed server, the way an assistant would. Every row below is
        the server&apos;s own answer.
      </p>

      <button
        type="button"
        onClick={() => void run()}
        disabled={state === "running"}
        className="mt-6 rounded-[var(--radius-sm)] bg-[var(--primary)] px-5 py-3 text-sm font-medium text-[var(--primary-contrast)] transition-opacity hover:opacity-90 disabled:opacity-60"
      >
        {state === "running"
          ? "Talking to the server..."
          : state === "idle"
            ? "Start a session"
            : "Run it again"}
      </button>

      <div aria-live="polite">
        {state === "error" && (
          <p className="mt-6 rounded-[var(--radius-md)] border border-[var(--discuss)] bg-discuss-soft p-4 text-sm text-[var(--discuss)]">
            The live server could not be reached: {error}. Nothing is being
            shown in its place.
          </p>
        )}

        {steps.length > 0 && (
          <ol id="mcp-steps" className="mt-6 space-y-3">
            {steps.map((s, i) => (
              <li
                key={s.request}
                className="rounded-[var(--radius-md)] border border-line bg-surface p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <p className="max-w-[620px] text-sm font-medium text-ink">
                    <span className="mr-2 font-mono text-xs text-muted">{i + 1}</span>
                    {s.label}
                  </p>
                  <span
                    className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold ${
                      s.ok ? "bg-success-soft text-[var(--success)]" : "bg-discuss-soft text-[var(--discuss)]"
                    }`}
                  >
                    {s.status} {s.ok ? "OK" : "Unexpected"}
                  </span>
                </div>
                <p className="mt-2 font-mono text-[12px] text-muted">{s.request}</p>
                <p className="mt-1 text-sm leading-relaxed text-muted">{s.shows}</p>
              </li>
            ))}
          </ol>
        )}

        {state === "done" && vitals && (
          <div className="mt-6 rounded-[var(--radius-md)] border border-line bg-surface p-5">
            <div className="flex flex-wrap items-center gap-3">
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${TIER_CLASS[vitals.tier]}`}
              >
                {TIER_LABEL[vitals.tier] ?? vitals.tier}
              </span>
              {vitals.simulated && (
                <span className="rounded-full border border-line px-3 py-1 text-xs font-medium text-muted">
                  Simulated persona, labelled by the server itself
                </span>
              )}
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink">
              {humaniseExplanation(vitals.explanation[0] ?? "")}
            </p>
            <p className="mt-3 text-sm leading-relaxed text-muted">
              That is the same tier the dashboard above shows, because the
              assistant reads the same profile rather than a copy made for
              this panel. Five requests, one session, {ms}ms, from this
              browser to the deployed server. Four of the seven tools only
              read; the three that write are not called here. The endpoint
              is open to any MCP client:{" "}
              <code className="break-all rounded bg-primary-soft px-1.5 py-0.5 font-mono text-[12px]">
                {MCP_URL}
              </code>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
