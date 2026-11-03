"""Turn one or more Tracxn "Funding Rounds" Excel exports into the inputs analyze.py reads.

Export from Tracxn: Transactions > Funding Rounds, filter Country = India, Round = Seed + Series A,
and your date range; keep all four output sections (Funding Rounds, Investors in Funding Rounds,
Companies in Funding Rounds, Current View). Larger windows can be split across several exports.

usage: python load_tracxn.py <out_dir> export1.xlsx [export2.xlsx ...]
writes <out_dir>/rounds.pkl, inv.pkl, companies.pkl (newer exports win on company profiles)
"""
import os, sys, warnings
import pandas as pd

warnings.filterwarnings("ignore")


def sheet(xl, prefix):
    name = next(n for n in xl.sheet_names if n.startswith(prefix))
    d = pd.read_excel(xl, name, header=None)
    h = d.index[d.iloc[:, 0].astype(str).str.strip() == "SNo."][0]   # Tracxn puts a title block above the header row
    d.columns = d.iloc[h]
    return d.iloc[h + 1:].reset_index(drop=True)


def main(out, paths):
    os.makedirs(out, exist_ok=True)
    R, I, C = [], [], []
    for p in paths:
        xl = pd.ExcelFile(p)
        R.append(sheet(xl, "Funding Rounds")); I.append(sheet(xl, "1.2")); C.append(sheet(xl, "Companies"))
        print(p, len(R[-1]), "rounds")
    rounds = pd.concat(R).drop_duplicates(["Domain Name", "Round Date", "Round Name", "Round Amount (USD)"])
    inv = pd.concat(I).drop_duplicates(["Domain Name", "Round Date", "Round Name", "Investor Name"])
    comp = pd.concat(C[::-1]).drop_duplicates("Domain Name")
    for n, d in [("rounds", rounds), ("inv", inv), ("companies", comp)]:
        d.to_pickle(os.path.join(out, f"{n}.pkl")); print(n, d.shape)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
