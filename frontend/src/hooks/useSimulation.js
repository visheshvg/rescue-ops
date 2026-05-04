import { useState, useRef, useCallback } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_API_URL || '/api';

export default function useSimulation() {
  const [grid, setGrid]               = useState(null);
  const [agentStates, setAgentStates] = useState([]);
  const [stats, setStats]             = useState({ rescued: 0, total_steps: 0, critical_rescued: 0 });
  const [status, setStatus]           = useState('idle');
  const [message, setMessage]         = useState('');
  const [speed, setSpeed]             = useState(400);
  const [strategy, setStrategy]       = useState('greedy');

  const intervalRef = useRef(null);
  const doneRef     = useRef(false);

  const stopAutoPlay = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setStatus(prev => prev === 'running' ? 'paused' : prev);
  }, []);

  const generate = useCallback(async (config) => {
    try {
      setStatus('idle');
      setMessage('Generating...');
      stopAutoPlay();
      doneRef.current = false;

      const res = await axios.post(`${API}/generate_grid`, {
        ...config,
        strategy,
      }, { withCredentials: true });

      setGrid(res.data.grid);
      setAgentStates(res.data.agent_states);
      setStats(res.data.stats);
      setStatus('paused');
      setMessage('Grid ready. Press Play.');
    } catch (err) {
      setStatus('error');
      setMessage(err.response?.data?.error || 'Failed to generate grid.');
    }
  }, [strategy, stopAutoPlay]);

  const step = useCallback(async () => {
    if (doneRef.current) return;
    try {
      const res = await axios.post(`${API}/move`, {}, { withCredentials: true });
      setGrid(res.data.grid);
      setAgentStates(res.data.agent_states);
      setStats(res.data.stats);

      if (res.data.all_completed) {
        doneRef.current = true;
        stopAutoPlay();
        setStatus('done');
        setMessage('Mission complete!');
      }
    } catch (err) {
      stopAutoPlay();
      setStatus('error');
      setMessage('Step failed.');
    }
  }, [stopAutoPlay]);

  const startAutoPlay = useCallback(() => {
    if (doneRef.current || !grid) return;
    setStatus('running');
    intervalRef.current = setInterval(step, speed);
  }, [grid, speed, step]);

  const togglePlay = useCallback(() => {
    if (status === 'running') {
      stopAutoPlay();
    } else if (status === 'paused') {
      startAutoPlay();
    }
  }, [status, startAutoPlay, stopAutoPlay]);

  const changeSpeed = useCallback((newSpeed) => {
    setSpeed(newSpeed);
    if (status === 'running') {
      clearInterval(intervalRef.current);
      intervalRef.current = setInterval(step, newSpeed);
    }
  }, [status, step]);

  return {
    grid, agentStates, stats, status, message,
    speed, strategy,
    generate, step, togglePlay, changeSpeed,
    setStrategy,
  };
}
