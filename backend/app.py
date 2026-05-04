import os
import uuid
import threading
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from rescue_ai import (
    generate_grid, a_star, spread_fire,
    assign_tasks, greedy_order, random_order,
    AGENT_CAPACITY
)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-change-in-prod')
CORS(app, supports_credentials=True)

_sessions = {}
_lock = threading.Lock()


def get_state():
    sid = session.get('sid')
    if not sid:
        session['sid'] = sid = str(uuid.uuid4())
    with _lock:
        if sid not in _sessions:
            _sessions[sid] = {
                'grid': None,
                'agent_states': [],
                'claimed': {},
                'stats': {'rescued': 0, 'total_steps': 0,
                          'critical_rescued': 0, 'total_survivors': 0},
            }
    return _sessions[sid]


def init_agent_states(grid):
    return [
        {
            'position':       list(a['position']),
            'original_pos':   list(a['position']),
            'type':           a['type'],
            'steps':          0,
            'carrying':       [],
            'completed':      False,
            'current_target': None,
            'path':           [],
            'task_queue':     grid['assignments'].get(str(tuple(a['position'])), []),
        }
        for a in grid['agents']
    ]


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200


@app.route('/api/generate_grid', methods=['POST'])
def generate_grid_route():
    state = get_state()
    data  = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON body'}), 400

    try:
        num_agents    = max(1, min(int(data.get('num_agents',    2)),  6))
        num_survivors = max(1, min(int(data.get('num_survivors', 6)), 20))
        num_obstacles = max(0, min(int(data.get('num_obstacles', 10)), 30))
        num_fire      = max(0, min(int(data.get('num_fire',      2)),  8))
        rows          = max(8, min(int(data.get('rows',         14)), 30))
        cols          = max(8, min(int(data.get('cols',         14)), 30))
        strategy      = data.get('strategy', 'greedy')
        if strategy not in ('greedy', 'random'):
            strategy = 'greedy'
    except (ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid parameter: {e}'}), 400

    try:
        grid = generate_grid(num_agents, num_survivors, num_obstacles,
                             num_fire, rows, cols, strategy)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    state['grid']         = grid
    state['agent_states'] = init_agent_states(grid)
    state['claimed']      = {}
    state['stats']        = {
        'rescued': 0, 'total_steps': 0,
        'critical_rescued': 0, 'total_survivors': num_survivors,
    }

    return jsonify({
        'success':      True,
        'grid':         _serialise_grid(grid),
        'agent_states': state['agent_states'],
        'stats':        state['stats'],
    }), 200


# ── Agent-type abilities ───────────────────────────────────────────────────────
#
#  MEDIC       capacity=2, normal speed, blocked by fire.
#              Picks up a 2nd nearby survivor before heading to exit.
#
#  SCOUT       capacity=1, DOUBLE speed (2 steps/turn), blocked by fire.
#              Always re-evaluates target; interrupts for closer critical.
#
#  FIREFIGHTER capacity=1, normal speed, walks THROUGH fire.
#              A* only avoids static obstacles — can reach fire-surrounded survivors.
#              Protected from fire-consumption: survivors it's targeting are
#              not deleted until the firefighter either rescues or abandons them.
#
# ─────────────────────────────────────────────────────────────────────────────

def _move_one_step(agent, idx, survivors, claimed, static_obstacles,
                   fire_cells, all_obstacles, exits, rows, cols, stats, strategy):
    """
    Executes exactly one movement step for the given agent.
    Returns True if a step was taken (or attempted), False if nothing to do.
    Modifies agent, survivors, claimed, stats in-place.
    """
    if agent['completed']:
        return False

    pos        = tuple(agent['position'])
    agent_type = agent['type']
    capacity   = AGENT_CAPACITY[agent_type]

    # Firefighter ignores fire as an obstacle
    agent_obs = static_obstacles if agent_type == 'firefighter' else all_obstacles

    def best_exit_path(p):
        opts = [(a_star(p, ex, agent_obs, rows, cols), ex) for ex in exits]
        opts = [(path, ex) for path, ex in opts if path]
        return min(opts, key=lambda x: len(x[0])) if opts else ([], None)

    # ── Carrying → head to exit ───────────────────────────────────────────
    if agent['carrying']:

        # FIX Gap 1 — MEDIC: if below capacity, grab a nearby survivor first
        if agent_type == 'medic' and len(agent['carrying']) < capacity:
            nearby = [
                s for s in survivors
                if s['id'] not in claimed or claimed[s['id']] == idx
            ]
            if nearby:
                path_to_exit, nearest_exit = best_exit_path(pos)
                exit_dist = len(path_to_exit) if path_to_exit else 9999
                if strategy == 'greedy':
                    nearby = greedy_order(nearby, pos)
                detour_candidate = nearby[0]
                detour_path = a_star(pos, tuple(detour_candidate['position']),
                                     agent_obs, rows, cols)
                # Detour only if survivor is closer than the exit
                if detour_path and len(detour_path) < exit_dist:
                    agent['current_target'] = detour_candidate['id']
                    claimed[detour_candidate['id']] = idx
                    agent['path'] = [list(p) for p in detour_path]
                    nxt = tuple(detour_path[0])
                    agent['position'] = list(nxt)
                    agent['steps']   += 1
                    stats['total_steps'] += 1
                    if nxt == tuple(detour_candidate['position']):
                        stats['rescued'] += 1
                        if detour_candidate['severity'] == 'critical':
                            stats['critical_rescued'] += 1
                        agent['carrying'].append({'id': detour_candidate['id'],
                                                  'severity': detour_candidate['severity']})
                        claimed.pop(detour_candidate['id'], None)
                        agent['current_target'] = None
                        agent['path'] = []
                        survivors[:] = [s for s in survivors if s['id'] != detour_candidate['id']]
                    return True

        path, tgt_exit = best_exit_path(pos)
        if path:
            agent['path']     = [list(p) for p in path]
            nxt               = tuple(path[0])
            agent['position'] = list(nxt)
            agent['steps']   += 1
            stats['total_steps'] += 1
            if nxt == tgt_exit:
                agent['carrying']       = []
                agent['current_target'] = None
                agent['path']           = []
                if not survivors:
                    agent['completed'] = True
        else:
            # FIX Gap 2: exit blocked by fire — can't return, mark complete
            agent['completed'] = True

        return True

    # ── Nothing left → return to exit ─────────────────────────────────────
    remaining = {s['id']: s for s in survivors}
    if not remaining:
        path, tgt_exit = best_exit_path(pos)
        if path:
            agent['path']     = [list(p) for p in path]
            nxt               = tuple(path[0])
            agent['position'] = list(nxt)
            agent['steps']   += 1
            stats['total_steps'] += 1
            if nxt == tgt_exit:
                agent['completed'] = True
        else:
            # FIX Gap 2: exit blocked — mark complete
            agent['completed'] = True
        return True

    # ── Pick a target ─────────────────────────────────────────────────────
    if agent['current_target'] is None:
        if agent_type == 'scout':
            candidates = [
                s for s in survivors
                if s['id'] not in claimed or claimed[s['id']] == idx
            ]
        else:
            candidates = [
                t for t in agent['task_queue']
                if t['id'] in remaining
                and (t['id'] not in claimed or claimed[t['id']] == idx)
            ]
            if not candidates:
                candidates = [
                    s for s in survivors
                    if s['id'] not in claimed or claimed[s['id']] == idx
                ]
        if not candidates:
            return False
        if strategy == 'greedy':
            candidates = greedy_order(candidates, pos)
        target = candidates[0]
        agent['current_target'] = target['id']
        claimed[target['id']]   = idx

    # ── Scout: interrupt for closer critical mid-route ─────────────────────
    target_id = agent['current_target']
    if target_id not in remaining:
        claimed.pop(target_id, None)
        agent['current_target'] = None
        agent['task_queue'] = [t for t in agent['task_queue'] if t['id'] != target_id]
        return False

    target     = remaining[target_id]
    target_pos = tuple(target['position'])

    if agent_type == 'scout' and target['severity'] != 'critical':
        closer_criticals = [
            s for s in survivors
            if s['severity'] == 'critical'
            and (s['id'] not in claimed or claimed[s['id']] == idx)
            and s['id'] != target_id
        ]
        if closer_criticals:
            # FIX Gap 5: cache path lengths to avoid triple A* calls
            crit_paths  = {s['id']: (a_star(pos, tuple(s['position']), agent_obs, rows, cols) or [])
                           for s in closer_criticals}
            nearest_crit = min(closer_criticals, key=lambda s: len(crit_paths[s['id']]) or 9999)
            crit_dist    = len(crit_paths[nearest_crit['id']]) or 9999
            curr_dist    = len(a_star(pos, target_pos, agent_obs, rows, cols) or []) or 9999

            if crit_dist < curr_dist and crit_dist < 9999:
                claimed.pop(target_id, None)
                target     = nearest_crit
                target_id  = nearest_crit['id']
                target_pos = tuple(nearest_crit['position'])
                agent['current_target'] = target_id
                claimed[target_id]      = idx

    # ── Pathfind and step ─────────────────────────────────────────────────
    path = a_star(pos, target_pos, agent_obs, rows, cols)
    if not path:
        claimed.pop(target_id, None)
        agent['current_target'] = None
        agent['task_queue'] = [t for t in agent['task_queue'] if t['id'] != target_id]
        agent['path'] = []
        return False

    agent['path'] = [list(p) for p in path]
    nxt           = tuple(path[0])
    agent['position'] = list(nxt)
    agent['steps']   += 1
    stats['total_steps'] += 1

    if nxt == target_pos:
        stats['rescued'] += 1
        if target['severity'] == 'critical':
            stats['critical_rescued'] += 1
        agent['carrying'].append({'id': target_id, 'severity': target['severity']})
        claimed.pop(target_id, None)
        agent['current_target'] = None
        agent['task_queue'] = [t for t in agent['task_queue'] if t['id'] != target_id]
        agent['path'] = []
        survivors[:] = [s for s in survivors if s['id'] != target_id]

    return True


@app.route('/api/move', methods=['POST'])
def move_agents():
    state = get_state()
    grid  = state['grid']
    if grid is None:
        return jsonify({'error': 'Grid not initialised'}), 400

    agent_states = state['agent_states']
    claimed      = state['claimed']
    stats        = state['stats']

    static_obstacles = set(map(tuple, grid['obstacles']))
    fire_cells       = set(map(tuple, grid['fire']))
    all_obstacles    = static_obstacles | fire_cells

    survivors  = grid['survivors']
    exits      = [tuple(e) for e in grid['exits']]
    rows, cols = grid['rows'], grid['cols']
    strategy   = grid.get('strategy', 'greedy')

    # FIX Gap 4: protect firefighter targets from fire-consumption
    # A firefighter actively targeting a survivor buys that survivor one more turn.
    firefighter_targets = {
        ag['current_target']
        for ag in agent_states
        if ag['type'] == 'firefighter' and ag['current_target'] is not None
    }

    consumed = [
        s for s in survivors
        if tuple(s['position']) in fire_cells
        and s['id'] not in firefighter_targets   # firefighter has priority
    ]
    for s in consumed:
        claimed.pop(s['id'], None)
        for ag in agent_states:
            ag['task_queue'] = [t for t in ag['task_queue'] if t['id'] != s['id']]
            if ag['current_target'] == s['id']:
                ag['current_target'] = None
    survivor_ids_consumed = {s['id'] for s in consumed}
    survivors[:] = [s for s in survivors if s['id'] not in survivor_ids_consumed]

    # ── Move each agent ───────────────────────────────────────────────────
    args = (survivors, claimed, static_obstacles, fire_cells,
            all_obstacles, exits, rows, cols, stats, strategy)

    for idx, agent in enumerate(agent_states):
        took_step = _move_one_step(agent, idx, *args)
        # Scout double speed: second step this turn
        if took_step and agent['type'] == 'scout' and not agent['completed']:
            _move_one_step(agent, idx, *args)

    # ── Spread fire every 6 steps ─────────────────────────────────────────
    grid['step'] += 1
    if grid['step'] % 6 == 0:
        new_fire = spread_fire(fire_cells, static_obstacles, rows, cols)
        grid['fire'] = [list(f) for f in new_fire]

    grid['survivors'] = survivors
    all_done = all(a['completed'] for a in agent_states)

    return jsonify({
        'success':       True,
        'grid':          _serialise_grid(grid),
        'agent_states':  agent_states,
        'stats':         stats,
        'all_completed': all_done,
    }), 200


@app.route('/api/reset', methods=['POST'])
def reset():
    state = get_state()
    state['grid']         = None
    state['agent_states'] = []
    state['claimed']      = {}
    state['stats'] = {'rescued': 0, 'total_steps': 0,
                      'critical_rescued': 0, 'total_survivors': 0}
    return jsonify({'success': True}), 200


def _serialise_grid(grid):
    return {
        'rows':      grid['rows'],
        'cols':      grid['cols'],
        'agents':    [{'position': list(a['position']), 'type': a['type']}
                      for a in grid['agents']],
        'survivors': [{'position': list(s['position']),
                       'severity': s['severity'], 'id': s['id']}
                      for s in grid['survivors']],
        'obstacles': [list(o) for o in grid['obstacles']],
        'fire':      [list(f) for f in grid['fire']],
        'exits':     [list(e) for e in grid['exits']],
        'strategy':  grid.get('strategy', 'greedy'),
        'step':      grid.get('step', 0),
    }


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)