import React from 'react';

export default function StatsPanel({ stats, grid, status }) {
  if (!stats) return null;

  const total     = stats.total_survivors || 0;
  const rescued   = stats.rescued || 0;
  const pct       = total > 0 ? ((rescued / total) * 100).toFixed(0) : '0';
  const remaining = grid?.survivors?.length ?? 0;
  const consumed  = Math.max(0, total - rescued - remaining);

  const rateColor = Number(pct) >= 80
    ? 'var(--green)'
    : Number(pct) >= 50
    ? 'var(--amber)'
    : 'var(--red)';

  // Avg steps per rescued survivor — lower is better
  const avgSteps = rescued > 0
    ? (stats.total_steps / rescued).toFixed(1)
    : '—';

  const cells = [
    { label: 'Rescued',          val: `${rescued}/${total}`,  color: 'var(--green)' },
    { label: 'Avg Steps/Rescue', val: avgSteps,               color: 'var(--purple)' },
    { label: 'Lost to Fire',     val: consumed,               color: consumed > 0 ? 'var(--orange)' : 'var(--text-muted)' },
    { label: 'Total Steps',      val: stats.total_steps || 0, color: 'var(--blue)' },
    { label: 'Rescue Rate',      val: `${pct}%`,              color: rateColor },
    { label: 'Strategy',         val: grid?.strategy ?? '—',  color: 'var(--text-muted)' },
  ];

  return (
    <div className="stats-strip">
      {cells.map(({ label, val, color }) => (
        <div key={label} className="stat-cell">
          <span className="stat-cell-label">{label}</span>
          <span className="stat-cell-val" style={{ color }}>{val}</span>
        </div>
      ))}
    </div>
  );
}