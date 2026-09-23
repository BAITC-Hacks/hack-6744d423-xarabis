"""Independent fictional district sandbox v2 rules; no real city dataset."""

DISTRICT_IMPROVEMENTS = {
    'bus': {'id': 'bus', 'name': 'Автобусы', 'cost': 22, 'zone_id': 'transport', 'gain': 24},
    'signals': {'id': 'signals', 'name': 'Умные светофоры', 'cost': 16, 'zone_id': 'transport', 'gain': 18},
    'park': {'id': 'park', 'name': 'Парк', 'cost': 18, 'zone_id': 'air', 'gain': 22},
    'filter': {'id': 'filter', 'name': 'Фильтры', 'cost': 26, 'zone_id': 'air', 'gain': 30},
    'school': {'id': 'school', 'name': 'Школа', 'cost': 32, 'zone_id': 'education', 'gain': 42},
    'repair': {'id': 'repair', 'name': 'Ремонт дорог', 'cost': 30, 'zone_id': 'transport', 'gain': 30},
}


def district_rules() -> dict:
    return {
        'rules_version': 'districts-v2', 'city_name': 'Новый Берег', 'fictional': True,
        'initial_budget': 200, 'quarter_income': 25, 'max_turns': 12,
        'target': 65, 'critical_below': 40, 'value_cap': 100,
        'rating_bands': {'red': '<40', 'yellow': '>=40 and <65', 'green': '>=65'},
        'win_condition': 'All three indicators must be >=65 in every one of the five districts',
        'initial_values': {
            'esil': {'transport': 70, 'air': 72, 'education': 54},
            'almaty': {'transport': 28, 'air': 52, 'education': 48},
            'saryarka': {'transport': 38, 'air': 24, 'education': 58},
            'baikonur': {'transport': 76, 'air': 74, 'education': 72},
            'nura': {'transport': 26, 'air': 42, 'education': 26},
        },
        'improvements': list(DISTRICT_IMPROVEMENTS.values()),
        'construction_limit_per_improvement_per_district': 1, 'max_improvements_per_turn': 3,
    }
