import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from rescue_ai import (
    manhattan_distance, a_star, greedy_order,
    spread_fire, generate_grid, random_free_pos,
    assign_tasks
)


def test_manhattan_same_point():
    assert manhattan_distance((3, 3), (3, 3)) == 0


def test_manhattan_horizontal():
    assert manhattan_distance((0, 0), (0, 5)) == 5


def test_manhattan_diagonal():
    assert manhattan_distance((0, 0), (3, 4)) == 7


def test_astar_direct_path():
    path = a_star((0, 0), (0, 3), set(), 5, 5)
    assert len(path) == 3
    assert path[-1] == (0, 3)


def test_astar_around_wall():
    obstacles = {(0,2),(1,2),(2,2),(3,2)}
    path = a_star((0, 0), (0, 4), obstacles, 5, 5)
    assert path
    assert path[-1] == (0, 4)
    for step in path:
        assert step not in obstacles


def test_astar_no_path():
    obstacles = {(0,1),(1,0)}
    path = a_star((0, 0), (1, 1), obstacles, 3, 3)
    assert path == []


def test_astar_same_start_goal():
    path = a_star((2, 2), (2, 2), set(), 5, 5)
    assert path == []


def test_astar_goal_is_obstacle():
    obstacles = {(1,1)}
    path = a_star((0, 0), (1, 1), obstacles, 5, 5)
    assert path == []


def test_greedy_empty():
    assert greedy_order([], (0, 0)) == []


def test_greedy_single():
    tasks = [{'position': (3, 3), 'severity': 'stable', 'id': 0}]
    result = greedy_order(tasks, (0, 0))
    assert result == tasks


def test_greedy_critical_first():
    tasks = [
        {'position': (10, 10), 'severity': 'critical', 'id': 0},
        {'position': (1, 1),   'severity': 'stable',   'id': 1},
    ]
    result = greedy_order(tasks, (0, 0))
    critical_idx = next(i for i, t in enumerate(result) if t['severity'] == 'critical')
    stable_idx   = next(i for i, t in enumerate(result) if t['severity'] == 'stable')
    assert critical_idx < stable_idx


def test_greedy_nearest_within_severity():
    tasks = [
        {'position': (0, 5), 'severity': 'stable', 'id': 0},
        {'position': (0, 2), 'severity': 'stable', 'id': 1},
    ]
    result = greedy_order(tasks, (0, 0))
    assert result[0]['id'] == 1


def test_fire_spread_increases_or_stays():
    fire = {(5, 5)}
    new_fire = spread_fire(fire, set(), 12, 12, spread_prob=1.0)
    assert len(new_fire) > len(fire)


def test_fire_spread_blocked_by_obstacles():
    fire = {(5, 5)}
    obstacles = {(4,5),(6,5),(5,4),(5,6)}
    new_fire = spread_fire(fire, obstacles, 12, 12, spread_prob=1.0)
    assert new_fire == fire


def test_fire_no_spread_at_zero_prob():
    fire = {(5, 5)}
    new_fire = spread_fire(fire, set(), 12, 12, spread_prob=0.0)
    assert new_fire == fire


def test_generate_grid_entity_counts():
    grid = generate_grid(2, 5, 8, num_fire=2, rows=12, cols=12)
    assert len(grid['agents']) == 2
    assert len(grid['survivors']) == 5
    assert len(grid['obstacles']) == 8
    assert len(grid['fire']) == 2


def test_generate_grid_no_overlaps():
    grid = generate_grid(3, 6, 10, num_fire=3, rows=15, cols=15)
    all_positions = (
        [a['position'] for a in grid['agents']] +
        [s['position'] for s in grid['survivors']] +
        grid['obstacles'] +
        grid['fire']
    )
    assert len(all_positions) == len(set(map(tuple, all_positions)))


def test_generate_grid_assignments_exist():
    grid = generate_grid(2, 4, 5, rows=12, cols=12, strategy='greedy')
    assert 'assignments' in grid
    assert len(grid['assignments']) == 2


def test_assign_tasks_all_survivors_assigned():
    survivors = [
        {'position': (1,1), 'severity': 'stable',   'id': 0},
        {'position': (3,3), 'severity': 'critical',  'id': 1},
        {'position': (9,9), 'severity': 'moderate',  'id': 2},
    ]
    agents = [(0,0), (10,10)]
    assignments = assign_tasks(survivors, agents, strategy='greedy')
    total_assigned = sum(len(v) for v in assignments.values())
    assert total_assigned == 3


def test_assign_tasks_no_survivors():
    assignments = assign_tasks([], [(0,0), (5,5)], strategy='greedy')
    assert all(len(v) == 0 for v in assignments.values())
