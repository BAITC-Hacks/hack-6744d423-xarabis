"""Fixed fictional game rules; no simulation or Astana reference data."""

SANDBOX_IMPROVEMENTS = {
    'bus': {'id': 'bus', 'name': 'Автобусы', 'cost': 22, 'zone_id': 'transport', 'gain': 24},
    'signals': {'id': 'signals', 'name': 'Умные светофоры', 'cost': 16, 'zone_id': 'transport', 'gain': 18},
    'park': {'id': 'park', 'name': 'Парк', 'cost': 18, 'zone_id': 'air', 'gain': 22},
    'filter': {'id': 'filter', 'name': 'Фильтры', 'cost': 26, 'zone_id': 'air', 'gain': 30},
    'school': {'id': 'school', 'name': 'Школа', 'cost': 32, 'zone_id': 'education', 'gain': 42},
}


def sandbox_rules() -> dict:
    return {
        'city_name': 'Новый Берег', 'fictional': True,
        'initial_budget': 100, 'quarter_income': 12, 'max_turns': 12,
        'target': 65, 'critical_below': 40, 'value_cap': 100,
        'initial_values': {'transport': 28, 'air': 34, 'education': 26},
        'improvements': list(SANDBOX_IMPROVEMENTS.values()),
        'construction_limit_per_improvement': 1, 'max_improvements_per_turn': 3,
    }
