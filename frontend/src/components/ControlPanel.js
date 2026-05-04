import React, { useState } from 'react';

function Field({ label, children }) {
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      {children}
    </div>
  );
}

function NumInput({ value, onChange, min, max }) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      onChange={e => onChange(Math.max(min, Math.min(max, Number(e.target.value))))}
    />
  );
}

// ── Grid reference data ───────────────────────────────────────────────────────
// Descriptions match the ACTUAL implemented backend logic — not aspirational.
const REFERENCE = [
  {
    group: 'Rescue Units',
    items: [
      {
        symbol: '🏥',
        color: '#9b59b6',
        name: 'Medic',
        desc: 'Carries 2 survivors per trip — fewest dropoff journeys',
        tag: 'cap ×2',
      },
      {
        symbol: '👁',
        color: '#1abc9c',
        name: 'Scout',
        desc: '2 path-steps per turn. Drops target mid-route for a closer critical',
        tag: 'speed ×2',
      },
      {
        symbol: '🧯',
        color: '#e67e22',
        name: 'Firefighter',
        desc: 'Treats fire as passable — only unit that can reach fire-surrounded survivors',
        tag: 'fire-proof',
      },
    ],
  },
  {
    group: 'Survivors',
    items: [
      { symbol: '🆘', color: '#ef4444', name: 'Critical', desc: 'Fire within 2 cells or 75%+ blocked — rescued first' },
      { symbol: '⚠',  color: '#f59e0b', name: 'Moderate', desc: 'Fire within 5 cells or 50%+ blocked' },
      { symbol: '●',  color: '#60a5fa', name: 'Stable',   desc: 'Open space, far from all hazards' },
    ],
  },
  {
    group: 'Environment',
    items: [
      { symbol: '🔥', color: '#fb923c', name: 'Fire',     desc: 'Spreads every 6 steps · capped at 25% of grid' },
      { symbol: '■',  color: '#3a3730', name: 'Obstacle', desc: 'Static — impassable for all units' },
      { symbol: '▣',  color: '#4ade80', name: 'Exit',     desc: 'Deliver survivors here to complete rescue' },
    ],
  },
];

export default function ControlPanel({
  onGenerate, onTogglePlay, onStep,
  status, strategy, onStrategyChange,
  speed, onSpeedChange,
}) {
  const [agents,    setAgents]    = useState(2);
  const [survivors, setSurvivors] = useState(8);
  const [obstacles, setObstacles] = useState(12);
  const [fire,      setFire]      = useState(3);
  const [rows,      setRows]      = useState(14);
  const [cols,      setCols]      = useState(14);

  const canPlay   = status === 'paused' || status === 'running';
  const isRunning = status === 'running';

  return (
    <>
      {/* ── Mission config ── */}
      <div className="panel-section">
        <div className="section-label">Mission Config</div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 10px' }}>
          <Field label="Rows">    <NumInput value={rows}      onChange={setRows}      min={8}  max={30} /></Field>
          <Field label="Cols">    <NumInput value={cols}      onChange={setCols}      min={8}  max={30} /></Field>
          <Field label="Agents">  <NumInput value={agents}    onChange={setAgents}    min={1}  max={6}  /></Field>
          <Field label="Survivors"><NumInput value={survivors} onChange={setSurvivors} min={1}  max={20} /></Field>
          <Field label="Obstacles"><NumInput value={obstacles} onChange={setObstacles} min={0}  max={30} /></Field>
          <Field label="Fire Zones"><NumInput value={fire}     onChange={setFire}      min={0}  max={8}  /></Field>
        </div>

        <Field label="Strategy">
          {/* Wrapper div needed for custom arrow — appearance:none removes native one */}
          <div style={{ position: 'relative' }}>
            <select
              value={strategy}
              onChange={e => onStrategyChange(e.target.value)}
              style={{ paddingRight: 28 }}
            >
              <option value="greedy">greedy (smart)</option>
              <option value="random">random (baseline)</option>
            </select>
            <span style={{
              position: 'absolute', right: 10, top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--amber)', fontSize: 12,
              pointerEvents: 'none', userSelect: 'none',
            }}>▾</span>
          </div>
        </Field>

        <button
          className="btn btn-primary"
          style={{ marginTop: 6 }}
          onClick={() => onGenerate({
            num_agents: agents, num_survivors: survivors,
            num_obstacles: obstacles, num_fire: fire, rows, cols,
          })}
        >
          ⌗ Generate Grid
        </button>
      </div>

      {/* ── Playback ── */}
      <div className="panel-section">
        <div className="section-label">Playback</div>
        <div className="playback-controls" style={{ marginBottom: 12 }}>
          <button
            className={`btn btn-ghost ${isRunning ? 'active' : ''}`}
            onClick={onTogglePlay}
            disabled={!canPlay}
          >
            {isRunning ? '⏸ Pause' : '▶ Play'}
          </button>
          <button
            className="btn btn-ghost"
            onClick={onStep}
            disabled={!canPlay || isRunning}
          >
            › Step
          </button>
        </div>

        <div className="field">
          <span className="field-label">Interval</span>
          <div className="slider-row">
            <input
              type="range" min={80} max={1000} step={40} value={speed}
              onChange={e => onSpeedChange(Number(e.target.value))}
            />
            <span className="slider-val">{speed}ms</span>
          </div>
        </div>
      </div>

      {/* ── Merged grid reference ── */}
      <div className="panel-section">
        <div className="section-label">Grid Reference</div>

        {REFERENCE.map(({ group, items }) => (
          <div key={group} style={{ marginBottom: 14 }}>
            {/* Group header */}
            <div style={{
              fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase',
              color: 'var(--text-dim)', marginBottom: 6,
            }}>
              {group}
            </div>

            {/* Item cards */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {items.map(item => (
                <div key={item.name} style={{
                  display: 'flex', alignItems: 'flex-start', gap: 10,
                  padding: '7px 8px',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border)',
                  borderLeft: `3px solid ${item.color}`,
                  borderRadius: 2,
                }}>
                  {/* Symbol as it appears on the grid */}
                  <span style={{
                    fontSize: 16, width: 22, textAlign: 'center',
                    flexShrink: 0, lineHeight: 1, paddingTop: 1,
                    color: item.color,
                  }}>
                    {item.symbol}
                  </span>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
                      <span style={{
                        fontSize: 11, fontWeight: 600,
                        color: item.color, letterSpacing: '0.06em',
                      }}>
                        {item.name}
                      </span>
                      {/* Ability tag for units */}
                      {item.tag && (
                        <span style={{
                          fontSize: 9, padding: '1px 5px',
                          background: `${item.color}20`,
                          color: item.color,
                          border: `1px solid ${item.color}40`,
                          borderRadius: 2,
                          letterSpacing: '0.06em',
                          fontWeight: 500,
                        }}>
                          {item.tag}
                        </span>
                      )}
                    </div>
                    <div style={{
                      fontSize: 10, color: 'var(--text-muted)',
                      lineHeight: 1.5,
                    }}>
                      {item.desc}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}