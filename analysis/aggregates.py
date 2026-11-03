"""Build the public aggregate tables from the (private) company-level dataset.

Only counts, rates and odds ratios leave this script. Any cut with fewer than MIN_N startups is
suppressed, so no individual company can be singled out.

usage: python aggregates.py <dataset_tracxn.csv> <results dir> <out dir>
"""
import json, os, sys
import numpy as np
import pandas as pd
import statsmodels.api as sm
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("a", os.path.join(HERE, "analyze.py"))
a = importlib.util.module_from_spec(spec); sys.argv, argv = sys.argv[:1], sys.argv; spec.loader.exec_module(a); sys.argv = argv

MIN_N = 25          # smallest cell we publish
MIN_GROUP = 100     # smallest city / sector we publish a breakdown for
SIG = {k: (label, grp) for k, label, grp in a.SIGNALS}


def load(path):
    df = pd.read_csv(path)
    for c in df.columns:
        if set(df[c].dropna().astype(str).unique()) <= {"True", "False"}:
            df[c] = df[c].astype(str) == "True"
    return df


def adjusted_or(df, mask, sector_ctrl=True):
    """Odds ratio of a group vs everyone else, with all founder signals plus year and founding-year controls.
    City odds also control for sector; sector odds also control for city (never the group's own dimension)."""
    y = df.t1_lead.astype(float)
    sec = df["sector"].where(df["sector"].map(df["sector"].value_counts()) >= 60, "other")
    cols = {"y": df.year.astype(str), "f": df.founded_bkt.astype(str)}
    if sector_ctrl: cols["s"] = sec
    else: cols["c"] = df.city
    ctrl = pd.get_dummies(pd.DataFrame(cols), drop_first=True).astype(float)
    X = sm.add_constant(df[a.CORE].astype(float).join(ctrl).assign(g=mask.astype(float)))
    m = sm.Logit(y, X).fit(disp=0, method="bfgs", maxiter=300)
    b, se = m.params["g"], m.bse["g"]
    return np.exp(b), np.exp(b - 1.96 * se), np.exp(b + 1.96 * se), m.pvalues["g"]


def rates(sub, key):
    w = sub[sub[key]]; wo = sub[~sub[key]]
    return len(w), w.t1_lead.mean() if len(w) else np.nan, wo.t1_lead.mean() if len(wo) else np.nan


def main(ds_path, res_dir, out):
    os.makedirs(out, exist_ok=True)
    df = load(ds_path)
    df["city_label"] = df["city"].map({"bengaluru": "Bengaluru", "mumbai": "Mumbai", "delhi_ncr": "Delhi NCR", "pune": "Pune",
                                       "hyderabad": "Hyderabad", "chennai": "Chennai", "other": "Other cities"})

    # 1. signal odds ratios, three windows
    for tag, name in [("", "2021-2026"), ("_2021-2024", "2021-2024"), ("_2025-2026", "2025-2026")]:
        r = pd.read_csv(os.path.join(res_dir, f"results_t1_lead{tag}.csv"))
        r = r[r.n >= MIN_N].assign(period=name)
        r[["period", "group", "signal", "label", "n", "rate_with", "rate_without", "odds_ratio", "lo", "hi", "p", "q"]] \
            .round(4).to_csv(os.path.join(out, f"signals_{name}.csv"), index=False)

    # 2. cities and sectors: size, raw tier-1 rate, adjusted odds vs the rest
    rows = []
    for col, kind in [("city_label", "city"), ("sector", "sector")]:
        for g, sub in df.groupby(col):
            if len(sub) < MIN_GROUP or g in ("other", "na", "Other cities"):
                continue
            o, lo, hi, p = adjusted_or(df, df[col] == g, sector_ctrl=(kind == "city"))
            rows.append(dict(kind=kind, name=g, startups=len(sub), tier1_led=int(sub.t1_lead.sum()), tier1_rate=sub.t1_lead.mean(),
                             iit_share=sub.iit.mean(), any_mba_share=sub.any_mba.mean(), no_elite_share=sub.no_elite_credential.mean(),
                             odds_vs_rest=o, lo=lo, hi=hi, p=p))
    pd.DataFrame(rows).round(4).to_csv(os.path.join(out, "groups.csv"), index=False)

    # 3. group x signal: raw tier-1 rates with / without each signal inside a city or sector (cells < MIN_N suppressed)
    rows = []
    for col, kind in [("city_label", "city"), ("sector", "sector")]:
        for g, sub in df.groupby(col):
            if len(sub) < MIN_GROUP or g in ("other", "na", "Other cities"):
                continue
            for k in SIG:
                n, rw, ro = rates(sub, k)
                if n < MIN_N or len(sub) - n < MIN_N:
                    continue
                rows.append(dict(kind=kind, name=g, signal=k, label=SIG[k][0], group=SIG[k][1], n_with=n, rate_with=rw, rate_without=ro,
                                 lift=rw / ro if ro else np.nan))
    pd.DataFrame(rows).round(4).to_csv(os.path.join(out, "group_signals.csv"), index=False)

    # 4. by year
    y = df[df.year != "na"].groupby("year").agg(startups=("t1_lead", "size"), tier1_led=("t1_lead", "sum"), tier1_rate=("t1_lead", "mean"),
                                                 iit_share=("iit", "mean"), any_mba_share=("any_mba", "mean"), lead_recorded=("lead_info", "mean"))
    y.round(4).to_csv(os.path.join(out, "years.csv"))

    # 5. MBA decomposition and credential ladder (already aggregate)
    e = json.load(open(os.path.join(res_dir, "extra.json")))
    pd.DataFrame([dict(mba=k, **v) for k, v in e["mba_decomp"].items()]).round(4).to_csv(os.path.join(out, "mba_decomposition.csv"), index=False)
    pd.DataFrame([dict(profile=k, tier1_rate=v[0], startups=v[1]) for k, v in e["ladder"].items() if v[1] >= MIN_N]).round(4) \
        .to_csv(os.path.join(out, "ladder.csv"), index=False)

    meta = json.load(open(os.path.join(res_dir, "meta.json")))
    meta.update(min_cell=MIN_N, min_group=MIN_GROUP, source="Tracxn export, Seed + Series A, India, 1 Jan 2021 - 2 Nov 2026")
    json.dump(meta, open(os.path.join(out, "meta.json"), "w"), indent=1)
    print("wrote", sorted(os.listdir(out)))


if __name__ == "__main__":
    main(*sys.argv[1:4])
