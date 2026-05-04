import React, { useMemo } from 'react';

const AGENT_COLORS = {
  medic:       '#9b59b6',
  scout:       '#1abc9c',
  firefighter: '#e67e22',
};

const SEVERITY_COLORS = {
  critical: '#ef4444',
  moderate: '#f59e0b',
  stable:   '#60a5fa',
};

export default function Grid({ grid, agentStates }) {
  if (!grid) return null;

  const { rows, cols } = grid;

  // Cell size: fit inside a ~620px wide container max, min 22px
  const CELL = Math.max(22, Math.min(46, Math.floor(580 / Math.max(rows, cols))));
  const GAP  = 1;

  // Build lookup sets for O(1) cell rendering
  const obstacleSet = useMemo(() =>
    new Set(grid.obstacles.map(o => `${o[0]},${o[1]}`)),
    [grid.obstacles]);

  const fireSet = useMemo(() =>
    new Set(grid.fire.map(f => `${f[0]},${f[1]}`)),
    [grid.fire]);

  const exitSet = useMemo(() =>
    new Set(grid.exits.map(e => `${e[0]},${e[1]}`)),
    [grid.exits]);

  const survivorMap = useMemo(() => {
    const m = {};
    grid.survivors.forEach(s => {
      m[`${s.position[0]},${s.position[1]}`] = s;
    });
    return m;
  }, [grid.survivors]);

  const pathSet = useMemo(() => {
    const s = new Set();
    agentStates.forEach(a => {
      (a.path || []).forEach(p => s.add(`${p[0]},${p[1]}`));
    });
    return s;
  }, [agentStates]);

  const agentMap = useMemo(() => {
    const m = {};
    agentStates.forEach(a => {
      const k = `${a.position[0]},${a.position[1]}`;
      if (!m[k]) m[k] = [];
      m[k].push(a);
    });
    return m;
  }, [agentStates]);

  function renderCell(row, col) {
    const key = `${row},${col}`;
    const isObstacle = obstacleSet.has(key);
    const isFire     = fireSet.has(key);
    const isExit     = exitSet.has(key);
    const survivor   = survivorMap[key];
    const agents     = agentMap[key];
    const isPath     = pathSet.has(key);

    // Base cell style
    let bg      = 'transparent';
    let border  = '1px solid rgba(255,255,255,0.04)';
    let content = null;
    let overlay = null;

    if (isObstacle) {
      bg = '#1e1c18';
      border = '1px solid #2a2720';
      content = (
        <div style={{
          width: '60%', height: '60%',
          background: '#2e2b26',
          borderRadius: 1,
        }} />
      );
    }

    if (isFire) {
      bg = 'rgba(251, 80, 20, 0.15)';
      border = '1px solid rgba(251, 80, 20, 0.3)';
      content = <span style={{ fontSize: CELL * 0.42, lineHeight: 1 }}>🔥</span>;
    }

    if (isPath && !isObstacle && !isFire && !survivor && !agents) {
      bg = 'rgba(245, 158, 11, 0.05)';
      overlay = (
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            width: 3, height: 3, borderRadius: '50%',
            background: 'rgba(245, 158, 11, 0.35)',
          }} />
        </div>
      );
    }

    if (isExit) {
      bg = 'rgba(74, 222, 128, 0.1)';
      border = '1px solid rgba(74, 222, 128, 0.25)';
      content = (
        <div style={{
          width: '55%', height: '55%',
          border: `2px solid rgba(74, 222, 128, 0.6)`,
          borderRadius: 1,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            width: '40%', height: '40%',
            background: 'rgba(74, 222, 128, 0.5)',
            borderRadius: 1,
          }} />
        </div>
      );
    }

    if (survivor) {
      const sc = SEVERITY_COLORS[survivor.severity];
      bg     = `${sc}18`;
      border = `1px solid ${sc}55`;
      const icons = { critical: '🆘', moderate: '⚠', stable: '●' };
      content = (
        <div style={{
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', gap: 1,
        }}>
          <span style={{
            fontSize: CELL * 0.34,
            color: sc,
            fontWeight: 600,
            lineHeight: 1,
          }}>
            {icons[survivor.severity]}
          </span>
        </div>
      );
      // Pulsing ring for critical
      if (survivor.severity === 'critical') {
        overlay = (
          <div style={{
            position: 'absolute', inset: 0,
            border: `1px solid ${sc}`,
            borderRadius: 1,
            animation: 'blink 1.2s ease-in-out infinite',
            pointerEvents: 'none',
          }} />
        );
      }
    }

    if (agents && agents.length > 0) {
      const a  = agents[0];
      const ac = AGENT_COLORS[a.type] || '#888';
      bg     = `${ac}22`;
      border = `1px solid ${ac}88`;
      const icons = { medic: '🏥', scout: '👁', firefighter: '🧯' };
      content = (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
          <span style={{ fontSize: CELL * 0.36, lineHeight: 1 }}>
            {agents.length > 1 ? `${agents.length}↑` : icons[a.type] || 'A'}
          </span>
          {CELL >= 32 && (
            <div style={{
              width: '70%', height: 2,
              background: ac,
              borderRadius: 1,
              opacity: 0.7,
            }} />
          )}
        </div>
      );
    }

    return (
      <div
        key={key}
        title={`(${row},${col})`}
        style={{
          width: CELL,
          height: CELL,
          background: bg,
          border,
          borderRadius: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          transition: 'background 0.25s, border-color 0.25s',
          flexShrink: 0,
        }}
      >
        {overlay}
        {content}
      </div>
    );
  }

  const totalW = cols * CELL + (cols - 1) * GAP;
  const totalH = rows * CELL + (rows - 1) * GAP;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
      {/* Coordinates header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        width: totalW,
        fontSize: 9,
        color: 'var(--text-dim)',
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
      }}>
        <span>(0,0)</span>
        <span>grid {rows}×{cols}</span>
        <span>({rows - 1},{cols - 1})</span>
      </div>

      {/* Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${cols}, ${CELL}px)`,
        gridTemplateRows:    `repeat(${rows}, ${CELL}px)`,
        gap: `${GAP}px`,
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid var(--border)',
        borderRadius: 2,
        padding: 2,
      }}>
        {Array.from({ length: rows }, (_, r) =>
          Array.from({ length: cols }, (_, c) => renderCell(r, c))
        )}
      </div>
    </div>
  );
}