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
    sum_df = sum_analysis(df)

    freq_df.to_csv(output_dir / "number_frequency_by_game.csv", index=False)
    pattern_df.to_csv(output_dir / "odd_even_patterns_by_game.csv", index=False)
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
    print(f"Most common odd/even pattern: {most_common_pattern['odd_even_pattern']} ({most_common_pattern['draws']} draws)")
    print(f"Historical sum range: {int(game_sums['min'])} to {int(game_sums['max'])}; median {game_sums['median']}")
    print(f"Monte Carlo target combination: {'-'.join(str(num) for num in target)}")
    print(f"Theoretical exact-match probability: {probability:.12f} (about 1 in {round(1 / probability):,})")
    print(f"Simulation hits: {int(sim_df.iloc[-1]['hits'])} of {args.simulations:,}")
    print(f"Suggested combinations saved: {len(suggestion_df)}")
    print(f"Outputs saved to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
