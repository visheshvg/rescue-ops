import React from 'react';

const TYPE_COLOR = {
  medic:       '#9b59b6',
  scout:       '#1abc9c',
  firefighter: '#e67e22',
};

const TYPE_ICON = {
  medic:       '🏥',
  scout:       '👁',
  firefighter: '🧯',
};

function AgentCard({ agent, idx }) {
  const color = TYPE_COLOR[agent.type] || '#888';
  const icon  = TYPE_ICON[agent.type] || '?';

  const statusLabel = agent.completed
    ? 'complete'
    : agent.carrying?.length > 0
    ? 'to exit'
    : 'searching';

  const statusClass = agent.completed
    ? 'tag-complete'
    : agent.carrying?.length > 0
    ? 'tag-to-exit'
    : 'tag-searching';

  return (
    <div
      className="agent-card"
      style={{ borderLeftColor: color, borderLeftWidth: 3 }}
    >
      <div className="agent-card-header">
        <span className="agent-card-title" style={{ color }}>
          {icon} {agent.type?.toUpperCase()} #{idx + 1}
        </span>
        <span className={`agent-status-tag ${statusClass}`}>
          {statusLabel}
        </span>
      </div>
      <div className="agent-card-body">
        <div className="agent-field">
          <span className="agent-field-label">Position</span>
          <span className="agent-field-val">
            {agent.position[0]},{agent.position[1]}
          </span>
        </div>
        <div className="agent-field">
          <span className="agent-field-label">Steps</span>
          <span className="agent-field-val" style={{ color: 'var(--amber)' }}>
            {agent.steps}
          </span>
        </div>
        <div className="agent-field" style={{ gridColumn: '1 / -1' }}>
          <span className="agent-field-label">Carrying</span>
          <span className="agent-field-val" style={{
            color: agent.carrying?.length > 0 ? 'var(--orange)' : 'var(--text-muted)',
          }}>
            {agent.carrying?.length > 0
              ? `${agent.carrying.length} survivor(s)`
              : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function AgentStatus({ agentStates, stats, grid }) {
  const total   = stats?.total_survivors || 0;
  const rescued = stats?.rescued || 0;
  const pct     = total > 0 ? (rescued / total) * 100 : 0;

  return (
    <>
      {/* Rescue progress */}
      {total > 0 && (
        <div className="rescue-bar-wrap">
          <div className="rescue-bar-header">
            <span style={{ color: 'var(--text-muted)', fontSize: 10, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
              Rescue Progress
            </span>
            <span style={{ color: 'var(--green)', fontSize: 11 }}>
              {rescued} / {total}
            </span>
          </div>
          <div className="rescue-bar-track">
            <div
              className="rescue-bar-fill"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Agent cards */}
      {agentStates.length > 0 ? (
        <div className="panel-section">
          <div className="section-label">Unit Telemetry</div>
          {agentStates.map((a, i) => (
            <AgentCard key={i} agent={a} idx={i} />
          ))}
        </div>
      ) : (
        <div className="panel-section" style={{ color: 'var(--text-dim)', fontSize: 11 }}>
          <div className="section-label">Unit Telemetry</div>
          No units deployed
        </div>
      )}

      {/* Fire status */}
      {grid && (
        <div className="panel-section">
          <div className="section-label">Environment</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              ['Fire cells', grid.fire?.length ?? 0, 'var(--orange)'],
              ['Step #',     grid.step ?? 0,          'var(--text-muted)'],
              ['Remaining',  grid.survivors?.length ?? 0, 'var(--blue)'],
              ['Lost to fire', Math.max(0, total - rescued - (grid.survivors?.length ?? 0)), 'var(--red)'],
            ].map(([label, val, color]) => (
              <div key={label} style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '6px 0',
                borderBottom: '1px solid var(--border)',
              }}>
                <span style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  {label}
                </span>
                <span style={{ fontSize: 13, color, fontWeight: 500 }}>
                  {val}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}