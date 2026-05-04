import React from 'react';
import useSimulation from './hooks/useSimulation';
import Grid from './components/Grid';
import ControlPanel from './components/ControlPanel';
import AgentStatus from './components/AgentStatus';
import StatsPanel from './components/StatsPanel';
import './App.css';

export default function App() {
  const {
    grid, agentStates, stats, status, message,
    speed, strategy,
    generate, step, togglePlay, changeSpeed, setStrategy,
  } = useSimulation();

  const isRunning = status === 'running';
  const isDone    = status === 'done';
  const isReady   = status === 'paused' || isRunning;

  return (
    <div className="app">

      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-left">
          <span className="app-title">Smart Disaster Rescue</span>
          <span className="app-sub">multi-agent · A* pathfinding · triage protocol</span>
        </div>
        <div className="header-right">
          <span className="header-badge">
            <span className={`status-dot ${isRunning ? 'active' : ''}`} />
            {isRunning ? 'sim active' : isDone ? 'mission complete' : 'standby'}
          </span>
          {grid && (
            <span className="header-badge">
              {grid.rows}×{grid.cols} · {grid.strategy}
            </span>
          )}
        </div>
      </header>

      {/* ── Left Sidebar — Config ── */}
      <aside className="app-sidebar">
        <ControlPanel
          onGenerate={generate}
          onTogglePlay={togglePlay}
          onStep={step}
          status={status}
          strategy={strategy}
          onStrategyChange={setStrategy}
          speed={speed}
          onSpeedChange={changeSpeed}
        />
      </aside>

      {/* ── Main — Grid ── */}
      <main className="app-main">
        <div className={`main-message-bar ${isDone ? 'success' : status === 'error' ? 'error' : ''}`}>
          <span style={{ color: 'var(--amber)', marginRight: 4 }}>›</span>
          {message || 'awaiting configuration'}
        </div>

        <div className="main-grid-area">
          {grid ? (
            <Grid grid={grid} agentStates={agentStates} />
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">⌗</div>
              <span>configure mission and generate grid</span>
            </div>
          )}
        </div>

        {/* Stats strip pinned to bottom of main */}
        <StatsPanel stats={stats} grid={grid} status={status} />
      </main>

      {/* ── Right — Telemetry ── */}
      <aside className="app-telem">
        <AgentStatus agentStates={agentStates} stats={stats} grid={grid} />
      </aside>

    </div>
  );
}