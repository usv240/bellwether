"use client";

/**
 * One picture of the only idea that matters here: your own normal range.
 *
 * Bellwether does not compare a person with a population, and that single
 * design choice is what separates it from the field it borrows its
 * features from. A paragraph explaining it competes with every other
 * paragraph. A band does not: the grey area is what this person's ordinary
 * days look like, the dots are days, and a day outside the band is only
 * remarkable relative to the band it left.
 *
 * Why an own baseline rather than a population is not an assertion here.
 * Measured on 349 real Supreme Court oral arguments, the spread between
 * two different speakers is smaller than the spread within one speaker's
 * own sessions on all nine features. A population comparison would be
 * asking a detector to resolve a difference smaller than the noise it has
 * to tolerate anyway.
 *
 * Colour is a signal and never decoration, which is the rule the health
 * dashboard literature is firmest about. Everything on this chart is
 * greyscale except the days that left the band, so a reader never has to
 * ask what a hue is doing.
 *
 * The numbers are the real composite scores from the committed drift
 * persona, the same file the engine tests assert against, not a shape
 * drawn to look convincing.
 */

/** Real composite scores, one per assessed day, from fixtures/personas/alex-drift. */
const SERIES = [
  -1.37, -1.77, 3.94, -1.96, -0.55, -1.2, 1.21, -0.88, -1.86, -1.0, -1.16,
  0.16, -1.79, 0.06, -1.2, 1.8, 0.04, -0.64, 1.06, 0.92, 0.63, -0.08, -0.01,
  0.38, -1.52, -1.56, 3.14, 3.33, 3.35, 5.05, 5.03, 9.92, 9.57, 11.31, 12.15,
  14.38, 16.52, 20.2, 20.99, 21.59, 26.09, 17.74, 19.1, 21.45, 25.69, 15.65,
  20.99,
];

/**
 * The band is the person's own ordinary range, taken from the days before
 * anything changed rather than chosen to frame the story well.
 */
const BAND_LOW = -2.5;
const BAND_HIGH = 4.0;

const W = 900;
const H = 150;
const PAD_X = 14;
const PAD_Y = 16;

const MIN = -4;
const MAX = 28;

const x = (i: number) => PAD_X + (i / (SERIES.length - 1)) * (W - PAD_X * 2);
const y = (v: number) =>
  PAD_Y + (1 - (v - MIN) / (MAX - MIN)) * (H - PAD_Y * 2);

export function BaselineBand() {
  const bandTop = y(BAND_HIGH);
  const bandBottom = y(BAND_LOW);

  return (
    <figure className="m-0">
      <figcaption className="sr-only">
        Forty-seven days of one person&apos;s speech measures. The shaded band
        is their own ordinary range. Days sit inside it for the first
        twenty-six days, then move above it and stay there.
      </figcaption>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-hidden="true"
      >
        {/* The band: everything this person's ordinary days look like. */}
        <rect
          x={PAD_X}
          y={bandTop}
          width={W - PAD_X * 2}
          height={bandBottom - bandTop}
          rx={4}
          fill="var(--band-fill)"
        />
        <line
          x1={PAD_X}
          x2={W - PAD_X}
          y1={bandTop}
          y2={bandTop}
          stroke="var(--band-edge)"
          strokeWidth={1}
          strokeDasharray="3 4"
        />
        <line
          x1={PAD_X}
          x2={W - PAD_X}
          y1={bandBottom}
          y2={bandBottom}
          stroke="var(--band-edge)"
          strokeWidth={1}
          strokeDasharray="3 4"
        />

        {SERIES.map((v, i) => {
          const outside = v > BAND_HIGH || v < BAND_LOW;
          return (
            <circle
              key={i}
              cx={x(i)}
              cy={y(v)}
              r={outside ? 3.6 : 2.8}
              fill={outside ? "var(--band-out)" : "var(--band-in)"}
            />
          );
        })}
      </svg>

      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px] text-muted">
        <span className="flex items-center gap-2">
          <span className="inline-block h-3 w-6 rounded-sm bg-[var(--band-fill)] ring-1 ring-[var(--band-edge)]" />
          Your own ordinary range
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-[var(--band-in)]" />
          A day inside it
        </span>
        <span className="flex items-center gap-2">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-[var(--band-out)]" />
          A day outside it
        </span>
      </div>
    </figure>
  );
}
