"use client";

// Beta mockup of the "Brewhouse" redesign (docs/design/brewhouse/DESIGN.md).
// Self-contained: sample data only, no API/socket calls, no shared components or global styles.

import { useEffect, useState } from "react";
import s from "./brewhouse.module.css";

type Theme = "light" | "stout" | "hop";

type Step = {
  name: string;
  target: number | null; // °C
  minutes: number;
  headline: (temp: string, left: number) => React.ReactNode;
};

const STEPS: Step[] = [
  { name: "Strike", target: 73, minutes: 25, headline: (t) => <>Heating strike water, <em>{t}°C</em> now.</> },
  { name: "Dough in", target: 66, minutes: 10, headline: () => <>Dough in. Stir well, <em>no dough balls</em>.</> },
  { name: "Mash", target: 66, minutes: 60, headline: (t, l) => <>Holding at <em>{t}°C</em><br />for another {l} min.</> },
  { name: "Mash out", target: 76, minutes: 10, headline: (t) => <>Mash out, raising to <em>{t}°C</em>.</> },
  { name: "Sparge", target: 76, minutes: 30, headline: () => <>Sparging to <em>27.8 L</em> pre-boil.</> },
  { name: "Boil", target: 100, minutes: 60, headline: (_t, l) => <>Rolling boil, <em>{l} min</em> to go.</> },
  { name: "Chill", target: 20, minutes: 25, headline: (t) => <>Chilling, <em>{t}°C</em> and falling.</> },
];

const ADDITIONS = [
  { name: "Challenger 25 g", when: "@60" },
  { name: "East Kent Goldings 20 g", when: "@15" },
  { name: "East Kent Goldings 30 g", when: "flame-out" },
];

export default function BrewhouseBetaPage() {
  const [theme, setTheme] = useState<Theme>("light");
  const [step, setStep] = useState(2);
  const [paused, setPaused] = useState(false);
  const [elapsed, setElapsed] = useState(22 * 60); // seconds into the current step
  const [wobble, setWobble] = useState(0.4);

  const current = STEPS[step];
  const target = current.target ?? 0;
  const temp = (target + wobble).toFixed(1);
  const left = Math.max(0, Math.ceil((current.minutes * 60 - elapsed) / 60));
  const mmss = (() => {
    const r = Math.max(0, current.minutes * 60 - elapsed);
    return `${String(Math.floor(r / 60)).padStart(2, "0")}:${String(r % 60).padStart(2, "0")}`;
  })();

  // Simulated live readings (beta only).
  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => {
      setElapsed((e) => e + 1);
      setWobble((w) => Math.max(-0.9, Math.min(0.9, w + (Math.random() - 0.5) * 0.2)));
    }, 1000);
    return () => clearInterval(id);
  }, [paused]);

  const next = () => {
    setStep((i) => Math.min(STEPS.length - 1, i + 1));
    setElapsed(0);
    setWobble(0);
  };

  // Marker position on the ±2 °C tolerance band.
  const markerLeft = `${Math.max(0, Math.min(100, ((wobble + 2) / 4) * 100))}%`;
  const inRange = Math.abs(wobble) <= 0.5;

  const vessels = [
    { name: "HLT", temp: "78°", note: "Sparge water", fill: step >= 4 ? 15 : 55, colour: "var(--water)", active: false },
    { name: "Mash", temp: step <= 3 ? `${temp}°` : "—", note: step <= 3 ? "Mashing" : "Spent grain", fill: step <= 4 ? 72 : 30, colour: "var(--malt)", active: step <= 3 },
    { name: "Kettle", temp: step >= 4 ? `${temp}°` : "—", note: step >= 4 ? "In use" : "Up next", fill: step >= 4 ? 80 : 0, colour: "var(--accent)", active: step >= 4 },
    { name: "FV1", temp: "19°", note: "Batch 041 · day 4", fill: 80, colour: "var(--hop)", active: false },
    { name: "FV2", temp: "—", note: "Clean", fill: 0, colour: "var(--hop)", active: false },
  ];

  return (
    <div className={s.root} data-theme={theme}>
      <div className={s.betaBar}>
        <span><strong>Beta mockup</strong>: sample data, readings are simulated. Nothing here talks to your controller.</span>
        <div className={s.themeSwitch} role="group" aria-label="Colour scheme">
          {(["light", "stout", "hop"] as Theme[]).map((t) => (
            <button
              key={t}
              type="button"
              className={`${s.pill} ${theme === t ? s.pillSolid : ""}`}
              aria-pressed={theme === t}
              onClick={() => setTheme(t)}
            >
              {t === "light" ? "Brewhouse" : t === "stout" ? "Stout (dark)" : "Hop yard"}
            </button>
          ))}
        </div>
      </div>

      <header className={s.header}>
        <div className={s.brand}>brew brain<span>.</span></div>
        <div className={s.mono} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13 }}>
          <span className={s.pill} style={{ background: "var(--card)" }}>Batch 042</span>
          <span>Sample Best Bitter · 23 L</span>
        </div>
      </header>

      <div className={s.row}>
        <section className={`${s.card} ${s.hero}`} aria-label="Current step">
          <div className={s.heroTop}>
            <span className={`${s.pill} ${s.pillAccent}`}>Step {step + 1} of {STEPS.length} · {current.name}</span>
            <span className={`${s.pill} ${s.mono} ${inRange ? s.pillOk : ""}`} style={!inRange ? { background: "var(--malt)" } : undefined}>
              ● {inRange ? "In range" : "Drifting"}
            </span>
          </div>

          <h1 className={s.headline}>{current.headline(temp, left)}</h1>

          <div>
            <div className={s.band} role="img" aria-label={`Temperature ${temp}°C against target ${target}°C`}>
              <div className={s.bandDanger} />
              <div className={s.bandWarn} />
              <div className={s.bandFine} />
              <div className={s.bandWarn} />
              <div className={s.bandDanger} />
              <div className={s.bandMarker} style={{ left: markerLeft }} />
            </div>
            <div className={`${s.bandScale} ${s.mono}`}>
              <span>{(target - 2).toFixed(1)}</span>
              <span>{(target - 1).toFixed(1)}</span>
              <span>{target.toFixed(1)} target</span>
              <span>{(target + 1).toFixed(1)}</span>
              <span>{(target + 2).toFixed(1)}</span>
            </div>
          </div>

          <div className={s.tiles}>
            <div className={s.tile}><div className={s.tileLabel}>Time left</div><div className={`${s.tileValue} ${s.mono}`}>{mmss}</div></div>
            <div className={s.tile}><div className={s.tileLabel}>Mash pH</div><div className={`${s.tileValue} ${s.mono}`}>5.32</div></div>
            <div className={s.tile}><div className={s.tileLabel}>Heater</div><div className={`${s.tileValue} ${s.mono}`}>{Math.round(42 - wobble * 20)}%</div></div>
            <div className={s.tile}><div className={s.tileLabel}>vs last 5</div><div className={`${s.tileValue} ${s.mono}`}>{wobble >= 0 ? "+" : ""}{wobble.toFixed(1)}°</div></div>
          </div>

          <div className={s.actions}>
            <button type="button" className={`${s.btn} ${s.btnPrimary}`} onClick={next} disabled={step === STEPS.length - 1}>
              {step < STEPS.length - 1 ? `Next: ${STEPS[step + 1].name.toLowerCase()} →` : "Brew complete"}
            </button>
            <button type="button" className={s.btn}>Add a note</button>
            <button type="button" className={s.btn} onClick={() => setPaused((p) => !p)}>{paused ? "Resume" : "Pause"}</button>
          </div>
        </section>

        <section className={s.panel} aria-label="Brewhouse vessels">
          <div className={`${s.panelHead} ${s.mono}`}>
            <span>BREWHOUSE · LIVE</span>
            <span className={s.mono} style={{ fontSize: 12, padding: "4px 10px", borderRadius: 999, background: "var(--accent)", color: "var(--on-accent)" }}>5 vessels</span>
          </div>
          <div className={s.vessels}>
            {vessels.map((v) => (
              <div key={v.name} className={s.vessel}>
                <div className={s.mono} style={{ fontSize: 12 }}>{v.temp}</div>
                <div className={`${s.tank} ${v.active ? s.tankActive : ""}`} aria-hidden="true">
                  <div className={s.tankFill} style={{ height: `${v.fill}%`, background: v.colour }} />
                </div>
                <div className={s.vesselName}>{v.name}</div>
                <div className={s.vesselNote}>{v.note}</div>
              </div>
            ))}
          </div>
          <div className={s.additions}>
            <div className={`${s.additionsTitle} ${s.mono}`}>UP NEXT IN THE BOIL</div>
            {ADDITIONS.map((a) => (
              <div key={a.name} className={s.addition}><span>{a.name}</span><span className={s.mono}>{a.when}</span></div>
            ))}
          </div>
        </section>
      </div>

      <section className={s.steps} aria-label="Brew steps">
        <span className={s.stepsTitle}>Today&apos;s brew</span>
        {STEPS.map((st, i) => (
          <span
            key={st.name}
            className={`${s.pill} ${i < step ? s.pillDone : i === step ? s.pillAccent : s.pillNext}`}
          >
            {i < step ? "✓ " : ""}{st.name}
          </span>
        ))}
        <span className={`${s.stepsMeta} ${s.mono}`}>OG 1.044 · FG 1.011 · 32 IBU · 4.3%</span>
      </section>
    </div>
  );
}
