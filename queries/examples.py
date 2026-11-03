"""Quick pandas versions of the example queries. Run from the repo root: python queries/examples.py"""
import pandas as pd

sig = pd.read_csv("data/signals_2021-2026.csv")
groups = pd.read_csv("data/groups.csv")
inside = pd.read_csv("data/group_signals.csv")

print("Top signals, all else equal:")
print(sig.sort_values("odds_ratio", ascending=False)[["label", "n", "odds_ratio", "lo", "hi", "q"]].round(2).head(10).to_string(index=False))

print("\nCities:")
print(groups[groups.kind == "city"].sort_values("odds_vs_rest", ascending=False)[["name", "startups", "tier1_rate", "odds_vs_rest", "p"]].round(3).to_string(index=False))

city = "Hyderabad"
print(f"\nInside {city} (raw rates):")
print(inside[(inside.kind == "city") & (inside.name == city)].sort_values("lift", ascending=False)[["label", "n_with", "rate_with", "rate_without", "lift"]].round(3).to_string(index=False))
