import argparse
import json
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


GAME_RULES = {
    "Ultra Lotto 6/58": {"pool": 58, "pick": 6, "replace": False, "ordered": False},
    "Grand Lotto 6/55": {"pool": 55, "pick": 6, "replace": False, "ordered": False},
    "Superlotto 6/49": {"pool": 49, "pick": 6, "replace": False, "ordered": False},
    "Megalotto 6/45": {"pool": 45, "pick": 6, "replace": False, "ordered": False},
    "Lotto 6/42": {"pool": 42, "pick": 6, "replace": False, "ordered": False},
    "6D Lotto": {"pool": 10, "pick": 6, "replace": True, "ordered": True},
    "4D Lotto": {"pool": 10, "pick": 4, "replace": True, "ordered": True},
    "3D Lotto 2PM": {"pool": 10, "pick": 3, "replace": True, "ordered": True},
    "3D Lotto 5PM": {"pool": 10, "pick": 3, "replace": True, "ordered": True},
    "3D Lotto 9PM": {"pool": 10, "pick": 3, "replace": True, "ordered": True},
    "2D Lotto 2PM": {"pool": 31, "pick": 2, "replace": False, "ordered": True},
    "2D Lotto 5PM": {"pool": 31, "pick": 2, "replace": False, "ordered": True},
    "2D Lotto 9PM": {"pool": 31, "pick": 2, "replace": False, "ordered": True},
    "EZ2 Lotto 11:30AM": {"pool": 31, "pick": 2, "replace": False, "ordered": True},
    "EZ2 Lotto 12:30PM": {"pool": 31, "pick": 2, "replace": False, "ordered": True},
    "EZ2 Lotto 2PM": {"pool": 31, "pick": 2, "replace": False, "ordered": True},
    "Suertres Lotto 11:30AM": {"pool": 10, "pick": 3, "replace": True, "ordered": True},
    "Suertres Lotto 12:30PM": {"pool": 10, "pick": 3, "replace": True, "ordered": True},
    "Suertres Lotto 2PM": {"pool": 10, "pick": 3, "replace": True, "ordered": True},
}

ULTRA_LOTTO_GAME = "Ultra Lotto 6/58"


def parse_numbers(combination):
    return [int(value) for value in re.findall(r"\d+", str(combination))]


def load_results(path):
    with open(path, encoding="utf-8") as file:
        records = json.load(file)

    df = pd.DataFrame(records)
    df["draw_date"] = pd.to_datetime(df["draw_date"], errors="coerce")
    df["numbers"] = df["combinations"].apply(parse_numbers)
    df["number_count"] = df["numbers"].apply(len)
    df["sum"] = df["numbers"].apply(sum)
    df["odd_count"] = df["numbers"].apply(lambda nums: sum(num % 2 for num in nums))
    df["even_count"] = df["number_count"] - df["odd_count"]
    df["odd_even_pattern"] = df["odd_count"].astype(str) + " odd / " + df["even_count"].astype(str) + " even"
    return df


def valid_draws(df):
    return df[df["number_count"] > 0].copy()


def invalid_draws(df):
    return df[df["number_count"] == 0].copy()


def frequency_analysis(df):
    exploded = df[["lotto_game", "numbers"]].explode("numbers")
    exploded = exploded.dropna(subset=["numbers"])
    exploded["numbers"] = exploded["numbers"].astype(int)
    return (
        exploded.groupby(["lotto_game", "numbers"])
        .size()
        .rename("frequency")
        .reset_index()
        .sort_values(["lotto_game", "frequency", "numbers"], ascending=[True, False, True])
    )


def pattern_analysis(df):
    return (
        df.groupby(["lotto_game", "odd_even_pattern"])
        .size()
        .rename("draws")
        .reset_index()
        .sort_values(["lotto_game", "draws"], ascending=[True, False])
    )


def daily_odd_even_analysis(df):
    """Summarize drawn odd and even numbers for each game on each date."""
    report = (
        df.assign(draw_date=df["draw_date"].dt.strftime("%Y-%m-%d"))
        .groupby(["draw_date", "lotto_game"], as_index=False)
        .agg(
            draws=("lotto_game", "size"),
            odd_numbers=("odd_count", "sum"),
            even_numbers=("even_count", "sum"),
        )
    )
    report["total_numbers"] = report["odd_numbers"] + report["even_numbers"]
    report["odd_percentage"] = (report["odd_numbers"] / report["total_numbers"] * 100).round(2)
    report["even_percentage"] = (report["even_numbers"] / report["total_numbers"] * 100).round(2)
    return report.sort_values(["draw_date", "lotto_game"], ascending=[False, True]).reset_index(drop=True)


def ultra_lotto_trend_analysis(df, recent_window=30, odd_even_weeks=4):
    """Compare recent Ultra Lotto draws with the complete available history.

    The report describes past draws only. Lottery draws remain random, so a
    higher trend score does not predict or improve the chance of a future win.
    """
    if recent_window <= 0:
        raise ValueError("recent_window must be greater than zero.")
    if odd_even_weeks <= 0:
        raise ValueError("odd_even_weeks must be greater than zero.")

    ultra_draws = (
        df[df["lotto_game"] == ULTRA_LOTTO_GAME]
        .dropna(subset=["draw_date"])
        .sort_values("draw_date", ascending=False)
        .copy()
    )
    if ultra_draws.empty:
        raise ValueError(f"No valid draws found for {ULTRA_LOTTO_GAME}.")

    recent_draws = ultra_draws.head(recent_window).copy()
    historical_frequency = (
        ultra_draws[["numbers"]]
        .explode("numbers")
        .groupby("numbers")
        .size()
        .rename("historical_frequency")
        .reset_index()
        .rename(columns={"numbers": "number"})
    )
    recent_frequency = (
        recent_draws[["numbers"]]
        .explode("numbers")
        .groupby("numbers")
        .size()
        .rename("recent_frequency")
        .reset_index()
        .rename(columns={"numbers": "number"})
    )

    trends = (
        pd.DataFrame({"number": range(1, GAME_RULES[ULTRA_LOTTO_GAME]["pool"] + 1)})
        .merge(historical_frequency, on="number", how="left")
        .merge(recent_frequency, on="number", how="left")
        .fillna(0)
    )
    trends[["historical_frequency", "recent_frequency"]] = trends[
        ["historical_frequency", "recent_frequency"]
    ].astype(int)
    trends["parity"] = np.where(trends["number"] % 2 == 0, "even", "odd")
    trends["historical_draw_percentage"] = (
        trends["historical_frequency"] / len(ultra_draws) * 100
    ).round(2)
    trends["recent_draw_percentage"] = (
        trends["recent_frequency"] / len(recent_draws) * 100
    ).round(2)
    trends["trend_delta_percentage_points"] = (
        trends["recent_draw_percentage"] - trends["historical_draw_percentage"]
    ).round(2)
    trends = trends.sort_values(
        ["trend_delta_percentage_points", "recent_frequency", "historical_frequency", "number"],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)

    moving_window_days = odd_even_weeks * 7
    moving_window_end = ultra_draws["draw_date"].max()
    moving_window_start = moving_window_end - pd.Timedelta(days=moving_window_days - 1)
    moving_odd_even_draws = ultra_draws[ultra_draws["draw_date"] >= moving_window_start].copy()

    if "odd_even_pattern" not in moving_odd_even_draws:
        moving_odd_even_draws["odd_even_pattern"] = (
            moving_odd_even_draws["odd_count"].astype(str)
            + " odd / "
            + moving_odd_even_draws["even_count"].astype(str)
            + " even"
        )
    recent_patterns = pattern_analysis(moving_odd_even_draws).copy()
    recent_patterns["draw_percentage"] = (
        recent_patterns["draws"] / len(moving_odd_even_draws) * 100
    ).round(2)
    recent_patterns = recent_patterns.sort_values(
        ["draws", "odd_even_pattern"], ascending=[False, True]
    ).reset_index(drop=True)
    recent_patterns.insert(0, "rank", range(1, len(recent_patterns) + 1))
    recent_patterns["moving_window_days"] = moving_window_days
    recent_patterns["moving_window_start"] = moving_window_start.strftime("%Y-%m-%d")
    recent_patterns["moving_window_end"] = moving_window_end.strftime("%Y-%m-%d")
    recent_patterns["moving_window_draws"] = len(moving_odd_even_draws)
    return trends, recent_patterns, recent_draws


def ultra_lotto_trend_suggestions(recent_draws, trends, patterns, suggestion_count=5, seed=42):
    """Create sample Ultra Lotto combinations that mirror historical trends only."""
    columns = [
        "rank",
        "suggested_combination",
        "odd_count",
        "even_count",
        "sum",
        "trend_score",
        "matches_recent_sum_range",
        "basis",
    ]
    if suggestion_count <= 0 or recent_draws.empty or patterns.empty:
        return pd.DataFrame(columns=columns)

    preferred_counts = pattern_counts(patterns.iloc[0]["odd_even_pattern"])
    if not preferred_counts:
        return pd.DataFrame(columns=columns)
    odd_needed, even_needed = preferred_counts
    if odd_needed + even_needed != GAME_RULES[ULTRA_LOTTO_GAME]["pick"]:
        return pd.DataFrame(columns=columns)

    trend_lookup = trends.set_index("number")
    odd_numbers = trend_lookup[trend_lookup["parity"] == "odd"].index.to_numpy(dtype=int)
    even_numbers = trend_lookup[trend_lookup["parity"] == "even"].index.to_numpy(dtype=int)
    if len(odd_numbers) < odd_needed or len(even_numbers) < even_needed:
        return pd.DataFrame(columns=columns)

    # Recent movement has extra weight, while every number keeps a nonzero chance.
    def weights_for(values):
        rows = trend_lookup.loc[values]
        return (
            1
            + rows["historical_frequency"].to_numpy(dtype=float)
            + rows["recent_frequency"].to_numpy(dtype=float) * 3
            + np.maximum(rows["trend_delta_percentage_points"].to_numpy(dtype=float), 0) / 10
        )

    odd_weights = weights_for(odd_numbers)
    even_weights = weights_for(even_numbers)
    median_sum = float(recent_draws["sum"].median())
    recent_std = float(recent_draws["sum"].std())
    tolerance = max(8, int(round(0 if pd.isna(recent_std) else recent_std)))
    min_sum, max_sum = median_sum - tolerance, median_sum + tolerance
    pattern_window_days = int(patterns.iloc[0].get("moving_window_days", 28))
    pattern_window_start = patterns.iloc[0].get("moving_window_start", "latest rolling window")
    pattern_window_end = patterns.iloc[0].get("moving_window_end", "latest draw")
    rng = np.random.default_rng(seed)
    suggestions = []
    seen = set()

    def add_combo(combo):
        combo = tuple(sorted(int(number) for number in combo))
        if combo in seen:
            return False
        seen.add(combo)
        combo_sum = sum(combo)
        rows = trend_lookup.loc[list(combo)]
        suggestions.append({
            "rank": len(suggestions) + 1,
            "suggested_combination": "-".join(f"{number:02d}" for number in combo),
            "odd_count": sum(number % 2 for number in combo),
            "even_count": len(combo) - sum(number % 2 for number in combo),
            "sum": combo_sum,
            "trend_score": round(float(rows["trend_delta_percentage_points"].sum()), 2),
            "matches_recent_sum_range": min_sum <= combo_sum <= max_sum,
            "basis": (
                "historical analysis only: recent number movement, "
                f"{pattern_window_days}-day moving odd/even pattern "
                f"({pattern_window_start} to {pattern_window_end}), and recent sum range; "
                "no winning outcome is predicted"
            ),
        })
        return True

    # First sample is a transparent deterministic baseline from the top trend rows.
    ranked_odds = trends[trends["parity"] == "odd"]["number"].to_numpy(dtype=int)
    ranked_evens = trends[trends["parity"] == "even"]["number"].to_numpy(dtype=int)
    baseline = np.concatenate([ranked_odds[:odd_needed], ranked_evens[:even_needed]])
    if min_sum <= baseline.sum() <= max_sum:
        add_combo(baseline)

    attempts = 0
    while len(suggestions) < suggestion_count and attempts < 20_000:
        attempts += 1
        combo = np.concatenate([
            weighted_choice_without_replacement(rng, odd_numbers, odd_weights, odd_needed),
            weighted_choice_without_replacement(rng, even_numbers, even_weights, even_needed),
        ])
        if min_sum <= combo.sum() <= max_sum:
            add_combo(combo)

    # Keep the requested report useful even when a narrow recent sum range has few combinations.
    while len(suggestions) < suggestion_count and attempts < 40_000:
        attempts += 1
        combo = np.concatenate([
            weighted_choice_without_replacement(rng, odd_numbers, odd_weights, odd_needed),
            weighted_choice_without_replacement(rng, even_numbers, even_weights, even_needed),
        ])
        add_combo(combo)

    return pd.DataFrame(suggestions, columns=columns)


def sum_analysis(df):
    return (
        df.groupby("lotto_game")["sum"]
        .agg(["count", "min", "median", "mean", "max", "std"])
        .round(2)
        .reset_index()
    )


def weighted_choice_without_replacement(rng, values, weights, size):
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    return rng.choice(values, size=size, replace=False, p=weights)


def weighted_choice_with_replacement(rng, values, weights, size):
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    return rng.choice(values, size=size, replace=True, p=weights)


def pattern_counts(pattern):
    match = re.match(r"(\d+) odd / (\d+) even", pattern)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def suggest_combinations(df, freq_df, pattern_df, sum_df, suggestions_per_game, seed):
    rng = np.random.default_rng(seed)
    suggestions = []

    for game in sorted(df["lotto_game"].unique()):
        rule = GAME_RULES.get(game)
        if not rule:
            continue

        game_freq = freq_df[freq_df["lotto_game"] == game].set_index("numbers")["frequency"]
        start = 0 if rule["replace"] else 1
        stop = rule["pool"] if rule["replace"] else rule["pool"] + 1
        values = np.arange(start, stop)
        weights = np.array([game_freq.get(value, 0) + 1 for value in values], dtype=float)

        game_patterns = pattern_df[pattern_df["lotto_game"] == game].sort_values("draws", ascending=False)
        if game_patterns.empty:
            continue
        preferred_pattern = game_patterns.iloc[0]["odd_even_pattern"]
        preferred_counts = pattern_counts(preferred_pattern)

        game_sum_stats = sum_df[sum_df["lotto_game"] == game].iloc[0]
        median_sum = float(game_sum_stats["median"])
        std_sum = float(game_sum_stats["std"]) if not pd.isna(game_sum_stats["std"]) else 0
        tolerance = max(3, int(round(std_sum * 0.75)))

        seen = set()
        attempts = 0
        game_suggestion_count = 0
        while game_suggestion_count < suggestions_per_game and attempts < 20_000:
            attempts += 1

            if rule["replace"]:
                combo = weighted_choice_with_replacement(rng, values, weights, rule["pick"])
            else:
                if preferred_counts and 0 < preferred_counts[0] < rule["pick"]:
                    odd_needed, even_needed = preferred_counts
                    odd_values = values[values % 2 == 1]
                    even_values = values[values % 2 == 0]
                    odd_weights = np.array([game_freq.get(value, 0) + 1 for value in odd_values], dtype=float)
                    even_weights = np.array([game_freq.get(value, 0) + 1 for value in even_values], dtype=float)
                    combo = np.concatenate([
                        weighted_choice_without_replacement(rng, odd_values, odd_weights, odd_needed),
                        weighted_choice_without_replacement(rng, even_values, even_weights, even_needed),
                    ])
                else:
                    combo = weighted_choice_without_replacement(rng, values, weights, rule["pick"])

            combo = [int(value) for value in combo]
            if not rule["ordered"]:
                combo = sorted(combo)

            combo_sum = sum(combo)
            if abs(combo_sum - median_sum) > tolerance:
                continue

            combo_key = tuple(combo)
            if combo_key in seen:
                continue
            seen.add(combo_key)

            odd_count = sum(value % 2 for value in combo)
            even_count = len(combo) - odd_count
            score = sum(game_freq.get(value, 0) for value in combo)
            suggestions.append({
                "lotto_game": game,
                "suggested_combination": "-".join(f"{value:02d}" for value in combo),
                "sum": combo_sum,
                "odd_even_pattern": f"{odd_count} odd / {even_count} even",
                "historical_frequency_score": int(score),
                "basis": "weighted by historical frequency, common odd/even pattern, and median-sum range",
            })
            game_suggestion_count += 1

    return pd.DataFrame(suggestions)


def exact_probability(rule):
    if rule["replace"] and rule["ordered"]:
        return 1 / (rule["pool"] ** rule["pick"])
    if rule["ordered"]:
        return 1 / math.perm(rule["pool"], rule["pick"])
    return 1 / math.comb(rule["pool"], rule["pick"])


def simulate_draws(rule, target, simulations, batch_size=100_000, seed=42):
    rng = np.random.default_rng(seed)
    target = np.array(target)
    if not rule["ordered"]:
        target = np.sort(target)

    hits = 0
    completed = 0
    checkpoints = []

    while completed < simulations:
        size = min(batch_size, simulations - completed)
        if rule["replace"]:
            draws = rng.integers(0, rule["pool"], size=(size, rule["pick"]))
        else:
            random_scores = rng.random((size, rule["pool"]))
            draws = np.argpartition(random_scores, rule["pick"], axis=1)[:, :rule["pick"]] + 1

        if not rule["ordered"]:
            draws.sort(axis=1)

        hits += int(np.all(draws == target, axis=1).sum())
        completed += size
        checkpoints.append({
            "simulations": completed,
            "hits": hits,
            "empirical_probability": hits / completed,
            "theoretical_probability": exact_probability(rule),
        })

    return pd.DataFrame(checkpoints)


def plot_frequency(freq_df, game_df, game, output_dir):
    rules = GAME_RULES.get(game)
    game_freq = freq_df[freq_df["lotto_game"] == game].copy()
    if rules:
        start = 0 if rules["replace"] else 1
        stop = rules["pool"] if rules["replace"] else rules["pool"] + 1
        full_range = pd.DataFrame({"numbers": range(start, stop)})
        game_freq = full_range.merge(game_freq[["numbers", "frequency"]], on="numbers", how="left").fillna(0)
    game_freq["numbers"] = game_freq["numbers"].astype(int)

    plt.figure(figsize=(14, 6))
    sns.barplot(data=game_freq, x="numbers", y="frequency", color="#287c8e")
    plt.title(f"Number Frequency - {game}")
    plt.xlabel("Number")
    plt.ylabel("Times drawn")
    plt.tight_layout()
    plt.savefig(output_dir / f"{safe_name(game)}_frequency.png", dpi=160)
    plt.close()

    ranked = game_freq.sort_values("frequency", ascending=False)
    least = ranked.tail(10).sort_values("frequency")
    most = ranked.head(10)
    pd.concat({"most_frequent": most, "least_frequent": least}).to_csv(
        output_dir / f"{safe_name(game)}_most_least_numbers.csv"
    )


def plot_patterns(pattern_df, game, output_dir):
    game_patterns = pattern_df[pattern_df["lotto_game"] == game]
    plt.figure(figsize=(10, 5))
    sns.barplot(data=game_patterns, x="odd_even_pattern", y="draws", color="#bc5a45")
    plt.title(f"Odd/Even Pattern Frequency - {game}")
    plt.xlabel("Pattern")
    plt.ylabel("Draws")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output_dir / f"{safe_name(game)}_odd_even_patterns.png", dpi=160)
    plt.close()


def plot_sums(game_df, game, output_dir):
    plt.figure(figsize=(10, 5))
    sns.histplot(game_df["sum"], bins=18, kde=True, color="#5b6c98")
    plt.title(f"Historical Sum Distribution - {game}")
    plt.xlabel("Sum of drawn numbers")
    plt.ylabel("Draws")
    plt.tight_layout()
    plt.savefig(output_dir / f"{safe_name(game)}_sum_distribution.png", dpi=160)
    plt.close()


def plot_monte_carlo(sim_df, game, output_dir):
    plt.figure(figsize=(10, 5))
    plt.plot(sim_df["simulations"], sim_df["empirical_probability"], label="Empirical hit rate")
    plt.axhline(sim_df["theoretical_probability"].iloc[0], color="#c94f4f", linestyle="--", label="Theoretical probability")
    plt.title(f"Monte Carlo Exact-Match Probability - {game}")
    plt.xlabel("Simulated draws")
    plt.ylabel("Probability")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / f"{safe_name(game)}_monte_carlo_probability.png", dpi=160)
    plt.close()


def safe_name(value):
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def main():
    parser = argparse.ArgumentParser(description="Analyze scraped PCSO lottery results.")
    parser.add_argument("--input", default="pcso_results.json", help="Path to scraped JSON results.")
    parser.add_argument("--output-dir", default="analysis_outputs", help="Directory for CSV and chart outputs.")
    parser.add_argument("--game", default="Ultra Lotto 6/58", help="Game to chart and simulate.")
    parser.add_argument("--simulations", type=int, default=200_000, help="Monte Carlo draw count.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible simulations.")
    parser.add_argument("--suggestions-per-game", type=int, default=3, help="Suggested combinations to generate per game.")
    parser.add_argument(
        "--ultra-trend-window",
        type=int,
        default=30,
        help="Number of latest Ultra Lotto 6/58 draws to compare with all history.",
    )
    parser.add_argument(
        "--ultra-trend-suggestions",
        type=int,
        default=5,
        help="Ultra Lotto 6/58 historical-analysis sample combinations to generate.",
    )
    parser.add_argument(
        "--ultra-odd-even-weeks",
        type=int,
        default=4,
        help="Calendar weeks in the rolling Ultra Lotto odd/even pattern basis.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_df = load_results(input_path)
    skipped_df = invalid_draws(raw_df)
    df = valid_draws(raw_df)
    if df.empty:
        raise SystemExit("No valid draw combinations found in input data.")

    if not skipped_df.empty:
        skipped_df.drop(columns=["numbers"], errors="ignore").to_csv(output_dir / "skipped_invalid_draws.csv", index=False)

    if args.game not in set(df["lotto_game"]):
        available = ", ".join(sorted(df["lotto_game"].unique()))
        raise SystemExit(f"Game not found: {args.game}. Available games: {available}")

    freq_df = frequency_analysis(df)
    pattern_df = pattern_analysis(df)
    daily_odd_even_df = daily_odd_even_analysis(df)
    sum_df = sum_analysis(df)

    freq_df.to_csv(output_dir / "number_frequency_by_game.csv", index=False)
    pattern_df.to_csv(output_dir / "odd_even_patterns_by_game.csv", index=False)
    daily_odd_even_df.to_csv(output_dir / "daily_odd_even_counts_by_game.csv", index=False)
    sum_df.to_csv(output_dir / "sum_statistics_by_game.csv", index=False)
    suggestion_df = suggest_combinations(
        df,
        freq_df,
        pattern_df,
        sum_df,
        suggestions_per_game=args.suggestions_per_game,
        seed=args.seed,
    )
    suggestion_df.to_csv(output_dir / "possible_winning_numbers_by_game.csv", index=False)

    ultra_trends, ultra_patterns, ultra_recent_draws = ultra_lotto_trend_analysis(
        df,
        recent_window=args.ultra_trend_window,
        odd_even_weeks=args.ultra_odd_even_weeks,
    )
    ultra_suggestions = ultra_lotto_trend_suggestions(
        ultra_recent_draws,
        ultra_trends,
        ultra_patterns,
        suggestion_count=args.ultra_trend_suggestions,
        seed=args.seed,
    )
    ultra_trends.to_csv(output_dir / "ultra_lotto_6_58_number_trends.csv", index=False)
    ultra_patterns.to_csv(output_dir / "ultra_lotto_6_58_recent_odd_even_patterns.csv", index=False)
    ultra_suggestions.to_csv(output_dir / "ultra_lotto_6_58_trend_suggestions.csv", index=False)

    game_df = df[df["lotto_game"] == args.game].copy()
    rule = GAME_RULES.get(args.game)
    if not rule:
        raise SystemExit(f"No Monte Carlo rule is configured for {args.game}.")

    target = game_df.iloc[0]["numbers"]
    sim_df = simulate_draws(rule, target, args.simulations, seed=args.seed)
    sim_df.to_csv(output_dir / f"{safe_name(args.game)}_monte_carlo.csv", index=False)

    plot_frequency(freq_df, game_df, args.game, output_dir)
    plot_patterns(pattern_df, args.game, output_dir)
    plot_sums(game_df, args.game, output_dir)
    plot_monte_carlo(sim_df, args.game, output_dir)

    most_common_pattern = pattern_df[pattern_df["lotto_game"] == args.game].iloc[0]
    game_sums = sum_df[sum_df["lotto_game"] == args.game].iloc[0]
    probability = exact_probability(rule)

    print(f"Loaded {len(raw_df)} total rows across {raw_df['lotto_game'].nunique()} games.")
    print(f"Analyzed {len(df)} valid draws across {df['lotto_game'].nunique()} games.")
    if not skipped_df.empty:
        print(f"Skipped {len(skipped_df)} rows with no parseable combination numbers.")
    print(f"Selected game: {args.game} ({len(game_df)} historical draws)")
    print(f"Daily odd/even rows saved: {len(daily_odd_even_df)}")
    print(f"Most common odd/even pattern: {most_common_pattern['odd_even_pattern']} ({most_common_pattern['draws']} draws)")
    print(f"Historical sum range: {int(game_sums['min'])} to {int(game_sums['max'])}; median {game_sums['median']}")
    print(
        f"Ultra Lotto trend report: {len(ultra_recent_draws)} recent draws, "
        f"{len(ultra_suggestions)} historical-analysis sample combinations, "
        f"{args.ultra_odd_even_weeks}-week rolling odd/even basis"
    )
    print(f"Monte Carlo target combination: {'-'.join(str(num) for num in target)}")
    print(f"Theoretical exact-match probability: {probability:.12f} (about 1 in {round(1 / probability):,})")
    print(f"Simulation hits: {int(sim_df.iloc[-1]['hits'])} of {args.simulations:,}")
    print(f"Suggested combinations saved: {len(suggestion_df)}")
    print(f"Outputs saved to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
