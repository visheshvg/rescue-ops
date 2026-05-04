import heapq
import random

AGENT_TYPES     = ['medic', 'scout', 'firefighter']
SEVERITY_LEVELS = ['critical', 'moderate', 'stable']
SEVERITY_PRIORITY = {'critical': 0, 'moderate': 1, 'stable': 2}
AGENT_CAPACITY    = {'medic': 2, 'scout': 1, 'firefighter': 1}


# ── A* pathfinding ────────────────────────────────────────────────────────────

def manhattan_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def a_star(start, goal, obstacles, rows, cols):
    """
    Returns shortest path start→goal (excluding start, including goal).
    Returns [] if no path exists or start == goal.
    """
    if start == goal:
        return []
    if goal in obstacles:
        return []

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score   = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = (current[0] + dx, current[1] + dy)
            if (0 <= neighbor[0] < rows
                    and 0 <= neighbor[1] < cols
                    and neighbor not in obstacles):
                tentative_g = g_score[current] + 1
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor]   = tentative_g
                    f = tentative_g + manhattan_distance(neighbor, goal)
                    heapq.heappush(open_set, (f, neighbor))
    return []


# ── Safe random placement ─────────────────────────────────────────────────────

def random_free_pos(occupied, rows, cols):
    """Returns a random (row, col) not in occupied. Mutates occupied."""
    max_attempts = rows * cols * 4
    for _ in range(max_attempts):
        pos = (random.randint(0, rows - 1), random.randint(0, cols - 1))
        if pos not in occupied:
            occupied.add(pos)
            return pos
    raise ValueError("Grid too crowded. Reduce entities or increase grid size.")


# ── Task ordering ─────────────────────────────────────────────────────────────

def greedy_order(tasks, start_pos):
    """Nearest-neighbour greedy sort. Critical survivors always go first."""
    if not tasks:
        return []

    critical = [t for t in tasks if t['severity'] == 'critical']
    others   = [t for t in tasks if t['severity'] != 'critical']

    def nn_sort(lst, origin):
        remaining = lst[:]
        ordered   = []
        current   = origin
        while remaining:
            nearest = min(remaining, key=lambda t: manhattan_distance(current, t['position']))
            ordered.append(nearest)
            current = nearest['position']
            remaining.remove(nearest)
        return ordered

    return nn_sort(critical, start_pos) + nn_sort(others, start_pos)


def random_order(tasks):
    shuffled = tasks[:]
    random.shuffle(shuffled)
    return shuffled


# ── K-means task assignment ───────────────────────────────────────────────────

def assign_tasks(survivors, agents, strategy='greedy'):
    """
    Clusters survivors to agents using k-means initialised from agent positions.
    Returns {str(agent_pos_tuple): [ordered survivor list]}.
    """
    if not survivors or not agents:
        return {str(agent): [] for agent in agents}

    k         = len(agents)
    centroids = list(agents)
    clusters  = [[] for _ in range(k)]

    for _ in range(15):
        clusters = [[] for _ in range(k)]
        for s in survivors:
            dists   = [manhattan_distance(s['position'], c) for c in centroids]
            min_idx = dists.index(min(dists))
            clusters[min_idx].append(s)
        for i in range(k):
            if clusters[i]:
                xs = [s['position'][0] for s in clusters[i]]
                ys = [s['position'][1] for s in clusters[i]]
                centroids[i] = (round(sum(xs) / len(xs)), round(sum(ys) / len(ys)))

    assignments = {}
    for idx, agent in enumerate(agents):
        cluster = clusters[idx]
        ordered = greedy_order(cluster, agent) if strategy == 'greedy' else random_order(cluster)
        assignments[str(agent)] = ordered

    return assignments


# ── Fire spreading ────────────────────────────────────────────────────────────

def spread_fire(fire_cells, obstacles, rows, cols, spread_prob=0.06):
    """
    Spreads fire to adjacent empty cells with spread_prob probability.
    Capped at 25% of total grid cells.
    """
    max_fire = int(rows * cols * 0.25)
    if len(fire_cells) >= max_fire:
        return fire_cells

    new_fire = set(fire_cells)
    for cell in fire_cells:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = (cell[0] + dx, cell[1] + dy)
            if (0 <= neighbor[0] < rows
                    and 0 <= neighbor[1] < cols
                    and neighbor not in obstacles
                    and neighbor not in fire_cells
                    and random.random() < spread_prob):
                new_fire.add(neighbor)
                if len(new_fire) >= max_fire:
                    return new_fire

    return new_fire


# ── Severity computation ──────────────────────────────────────────────────────

def compute_severity(pos, fire_cells, obstacle_set, rows, cols):
    """
    Assigns severity based on actual environmental danger.
    critical  → fire within 2 cells OR 75%+ neighbours blocked
    moderate  → fire within 5 cells OR 50%+ neighbours blocked
    stable    → open space, far from all hazards
    """
    if fire_cells:
        min_fire_dist = min(manhattan_distance(pos, f) for f in fire_cells)
    else:
        min_fire_dist = float('inf')

    neighbours = [(pos[0] + dx, pos[1] + dy) for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]]
    valid       = [n for n in neighbours if 0 <= n[0] < rows and 0 <= n[1] < cols]
    blocked     = sum(1 for n in valid if n in obstacle_set or n in fire_cells)
    trapped     = blocked / max(len(valid), 1)

    if min_fire_dist <= 2 or trapped >= 0.75:
        return 'critical'
    elif min_fire_dist <= 5 or trapped >= 0.50:
        return 'moderate'
    else:
        return 'stable'


# ── Grid generation ───────────────────────────────────────────────────────────

def generate_grid(num_agents, num_survivors, num_obstacles,
                  num_fire=2, rows=14, cols=14, strategy='greedy'):
    """
    Generates a fresh simulation state. No entities overlap.
    Survivor severity is derived from actual environment, not random weights.
    """
    occupied = set()

    # FIX Gap 3: reserve exit corners so agents/survivors never spawn on them
    exits = [(0, 0), (rows - 1, cols - 1)]
    for ex in exits:
        occupied.add(ex)

    obstacle_list = [random_free_pos(occupied, rows, cols) for _ in range(num_obstacles)]
    obstacle_set  = set(obstacle_list)

    fire_cells = set()
    for _ in range(num_fire):
        fire_cells.add(random_free_pos(occupied, rows, cols))

    agent_list = []
    for _ in range(num_agents):
        pos = random_free_pos(occupied, rows, cols)
        agent_list.append({'position': pos, 'type': random.choice(AGENT_TYPES)})

    survivor_list = []
    for i in range(num_survivors):
        pos      = random_free_pos(occupied, rows, cols)
        severity = compute_severity(pos, fire_cells, obstacle_set, rows, cols)
        survivor_list.append({'position': pos, 'severity': severity, 'id': i})

    agent_positions = [a['position'] for a in agent_list]
    assignments     = assign_tasks(survivor_list, agent_positions, strategy)

    return {
        'rows':        rows,
        'cols':        cols,
        'agents':      agent_list,
        'survivors':   survivor_list,
        'obstacles':   obstacle_list,
        'fire':        list(fire_cells),
        'exits':       exits,
        'assignments': assignments,
        'strategy':    strategy,
        'step':        0,
    }