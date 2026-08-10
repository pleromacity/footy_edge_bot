import nba_model


def _games(entries):
    """Builds fake API-Sports NBA game entries from (home_id, away_id, home_pts, away_pts) tuples."""
    return [
        {
            "teams": {"home": {"id": h_id}, "visitors": {"id": a_id}},
            "scores": {"home": {"points": h_pts}, "visitors": {"points": a_pts}},
        }
        for h_id, a_id, h_pts, a_pts in entries
    ]


def test_extract_team_strength_averages_correctly():
    games = _games([
        (1, 99, 110, 100),  # team 1 home, scores 110 concedes 100
        (88, 1, 105, 115),  # team 1 away, scores 115 concedes 105
    ])
    strength = nba_model.extract_team_strength(games, team_id=1)
    assert strength["avg_scored"] == (110 + 115) / 2
    assert strength["avg_conceded"] == (100 + 105) / 2
    assert strength["avg_scored_home"] == 110
    assert strength["avg_scored_away"] == 115
    assert strength["sample_size"] == 2


def test_extract_team_strength_ignores_games_team_not_in():
    games = _games([(50, 60, 100, 90)])
    strength = nba_model.extract_team_strength(games, team_id=1)
    assert strength["sample_size"] == 0


def test_expected_margin_favors_stronger_team():
    strong = {"avg_scored_home": 118, "avg_conceded_home": 104}
    weak = {"avg_scored_away": 100, "avg_conceded_away": 118}
    margin = nba_model.expected_margin(strong, weak)
    assert margin > 10  # clear projected home blowout


def test_expected_margin_includes_home_court_advantage():
    identical_home = {"avg_scored_home": 110, "avg_conceded_home": 110}
    identical_away = {"avg_scored_away": 110, "avg_conceded_away": 110}
    margin = nba_model.expected_margin(identical_home, identical_away)
    assert margin == nba_model.HOME_COURT_ADVANTAGE


def test_outcome_probabilities_sum_to_one():
    probs = nba_model.outcome_probabilities(margin=5.0)
    assert abs(probs["home_win"] + probs["away_win"] - 1.0) < 1e-9


def test_zero_margin_gives_fifty_fifty():
    probs = nba_model.outcome_probabilities(margin=0.0)
    assert abs(probs["home_win"] - 0.5) < 1e-9


def test_large_positive_margin_gives_dominant_home_favorite():
    probs = nba_model.outcome_probabilities(margin=25.0)
    assert probs["home_win"] > 0.95


def test_large_negative_margin_gives_dominant_away_favorite():
    probs = nba_model.outcome_probabilities(margin=-25.0)
    assert probs["away_win"] > 0.95


def test_probabilities_always_valid_range():
    for margin in [-40, -10, -1, 0, 1, 10, 40]:
        probs = nba_model.outcome_probabilities(margin=margin)
        assert 0.0 <= probs["home_win"] <= 1.0
        assert 0.0 <= probs["away_win"] <= 1.0
