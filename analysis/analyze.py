"""India founder signals, Tracxn edition.

Question (after Deedy Das's US study): among Indian startups that raised a Seed or Series A
between Jan 2021 and Dec 2024, which founder backgrounds go with getting a round LED by a
tier-1 Indian VC, all else equal?

Unit: company. Signals: "any founder has X", coded from Tracxn's Key People Info text
(founders only), Team Background tags and Founder Highlights. One logit with every signal
plus year / sector / city / founding-year controls; Benjamini-Hochberg q-values as in Deedy's chart.
"""
import os, re, sys, json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

D = sys.argv[1] if len(sys.argv) > 1 else "tracxn/"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
# optional round-date window, e.g. "2025-2026"; outcome and first-round year use rounds inside it only
PERIOD = sys.argv[3] if len(sys.argv) > 3 else "all"
TAG = "" if PERIOD == "all" else "_" + PERIOD

# ---- tier-1: the 15 funds that most consistently lead Indian seed / Series A rounds ----
# Tier-1 funds are kept out of the public repo. Put your own list in analysis/tier1.json
# (see tier1.example.json): {"funds": {"Display name": "regex matching Tracxn investor names", ...}}.
_cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tier1.json")
if not os.path.exists(_cfg):
    _cfg = _cfg.replace("tier1.json", "tier1.example.json")
TIER1 = json.load(open(_cfg))["funds"]
T1RE = re.compile("|".join(f"(?:{v})" for v in TIER1.values()), re.I)

# VC / PE firms whose ex-staff count as "ex-VC/PE" (founder worked there)
VCPE = (r"sequoia(?! consulting)|peak xv|\baccel\b(?! india portfolio)|lightspeed(?! mobility| photonics)(?!ai)|elevation capital|saif partners|(?<!tech)nexus venture|matrix partners|\bz47\b|"
        r"kalaari|blume|chiratae|idg ventures|helion|stellaris|tiger global|softbank|warburg|\bkkr\b|bain capital|"
        r"\btpg\b|blackstone|general atlantic|chryscapital|kedaara|everstone|multiples|temasek|\bgic\b|omidyar|"
        r"unitus|saama|prime venture|3one4|india quotient|venture highway|info edge ventures|fireside|\ba91\b|avataar|"
        r"steadview|eight roads|norwest|qualcomm ventures|elevar|orios|inventus|yournest|ventureast|ankur capital|"
        r"aavishkaar|beenext|jungle ventures|iron pillar|lok capital|caspian|general catalyst|bessemer|"
        r"venture capital|private equity|\bvc fund|ventures? partner|investment (associate|principal)")
T1_STAFF = json.load(open(_cfg))["staff_regex"]  # ex-staff of the same tier-1 funds, matched in employer text
BIGTECH = r"google|microsoft|amazon|\bmeta\b|facebook|apple|\buber\b|linkedin|netflix|adobe|salesforce|oracle|intel\b|cisco|nvidia|qualcomm|ibm\b|sap\b|vmware"
UNICORN = (r"flipkart|swiggy|zomato|\bola\b|ola cabs|ola electric|paytm|\boyo\b|razorpay|\bcred\b|phonepe|meesho|byju|"
           r"zerodha|freshworks|unacademy|dream11|myntra|nykaa|policybazaar|delhivery|udaan|zetwerk|groww|sharechat|"
           r"inmobi|bigbasket|dunzo|cars24|lenskart|urban company|urbanclap|rapido|zepto|blinkit|grofers|mpl|"
           r"mobile premier league|vedantu|upgrad|slice\b|jupiter|khatabook|bharatpe|pine labs|druva|postman|"
           r"browserstack|chargebee|innovaccer|icertis|hasura|darwinbox|mamaearth|boat\b|licious|curefit|cult\.?fit|"
           r"rebel foods|physicswallah|spinny|acko|digit insurance|open financial|ofbusiness|infra\.market|moglix|"
           r"glance|dailyhunt|verse innovation|games24x7|pristyn|cardekho|droom|snapdeal|quikr|makemytrip|"
           r"shiprocket|leadsquared|apna\b|unacademy|eruditus|purplle|firstcry|xpressbees|ecom express|"
           r"livspace|pharmeasy|1mg|practo|mfine|healthifyme|cult|uniphore|gupshup|yellow\.ai|perfios")
MBB = r"mckinsey|boston consulting|\bbcg\b|\bbain\b(?! capital)"
IBANK = r"goldman|morgan stanley|j\.?p\.? ?morgan|jpmorgan|citi(bank|group)?\b|deutsche bank|barclays|credit suisse|ubs\b|bank of america|merrill|nomura|kotak investment banking|avendus|jm financial|lazard|rothschild|hsbc|investment bank"

MBA_TOKEN = r"\b(MBA|M\.B\.A|PGDM|PGP|PGPM|PGDBM|PGDBA|PGPX|EMBA|PGP ?ABM|Post ?Graduate (Program|Programme|Diploma) in (Business )?Management|Master of Business Administration|MBA/)"
EXEC = r"\b(EMBA|PGPX|PGPMAX|ePGP|EPGP|Executive|PGPPRO|PGDM ?\(?Executive|Exec\b|Online)"
IIM_ABC = r"IIM[\s,–-]*(Ahmedabad|Bangalore|Bengaluru|Calcutta|Kolkata|A\b|B\b|C\b)|Indian Institute of Management[\s,–-]*(Ahmedabad|Bangalore|Bengaluru|Calcutta|Kolkata)"
IIM_ANY = r"\bIIM\b|Indian Institute Of Management"
ISB = r"\bISB\b|Indian School of Business"
ELITE_FOREIGN_BS = (r"Harvard|Stanford|Wharton|University of Pennsylvania|INSEAD|London Business School|\bLBS\b|Kellogg|"
                    r"Northwestern|Booth|University of Chicago|Columbia|MIT\b|Sloan|Massachusetts Institute|Haas|Berkeley|"
                    r"Tuck|Dartmouth|Yale|Ross|University of Michigan|Stern|NYU|New York University|Fuqua|Duke|Darden|"
                    r"Oxford|Said Business|Cambridge|Judge|HEC Paris|IESE|IMD\b|Cornell|Johnson|UCLA|Anderson")
TOP_INDIAN_BS = r"XLRI|Faculty of Management Studies|\bFMS\b|Jamnalal Bajaj|\bJBIMS\b|SPJIMR|S\.?P\.? Jain Institute|\bMDI\b|Management Development Institute|IIFT|Indian Institute of Foreign Trade|NMIMS|Narsee Monjee|Symbiosis|SIBM"
IIT = r"\bIIT\b|Indian Institute of Technology"
TOP_UG_NON_IIT = r"\bBITS\b|Birla Institute of Technology|\bNIT\b|National Institute of Technology|\bIIIT|Delhi College of Engineering|\bDTU\b|Delhi Technological|\bNSIT|Netaji Subhas|Indian Institute of Science|\bIISc\b|Indian Statistical|\bSRCC\b|Shri Ram College|St\.? Stephen|College of Engineering,? (Pune|Guindy)|\bVJTI\b|Jadavpur"
ELITE_FOREIGN_UNI = (ELITE_FOREIGN_BS + r"|Carnegie Mellon|Caltech|California Institute of Technology|Princeton|Imperial College|"
                     r"University College London|\bUCL\b|London School of Economics|\bLSE\b|National University of Singapore|"
                     r"\bNUS\b|Nanyang|\bNTU\b|University of Toronto|Waterloo|ETH Zurich|Georgia (Institute of )?Tech|"
                     r"Purdue|University of Illinois|UIUC|University of Texas|University of Southern California|\bUSC\b|"
                     r"Johns Hopkins|Brown University|University of Washington|University of Wisconsin|Warwick|Edinburgh|King.s College")
ENG = r"\b(B\.?\s?Tech|BTech|B\.?E\.?\b|BE\b|M\.?\s?Tech|MTech|B\.?S\.? in (Computer|Electrical|Mechanical)|Computer Science|Engineering|B\.?Sc.*Computer|MS\b|M\.S\.)"
PHD = r"\bPh\.? ?D\b|\bPhD\b|Doctorate|DPhil"
CA = r"\bCA\b|Chartered Accountant|\bICAI\b"


def parse_people(text):
    """Key People Info -> list of founder dicts with raw description."""
    out = []
    for line in str(text).split("\n"):
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 2:
            continue
        name, role = parts[0], parts[1]
        rest = "; ".join(p for p in parts[2:] if "@" not in p)
        out.append({"name": name, "role": role, "desc": rest})
    return out


BOUNDARY = re.compile(r"(?:19|20)\d\d\b|\||\.\s|;|\b(?:BE|BTech|B\.Tech|BSc|BCom|BBA|BA|MS|MSc|MTech|MCA|PhD)\b,")


def segment_before(desc, pos):
    """Text of the education entry that ends at pos (institution names may contain commas)."""
    start = 0
    for b in BOUNDARY.finditer(desc, 0, pos):
        start = b.end()
    return desc[start:pos + 12]


def classify_school(seg):
    if re.search(IIM_ABC, seg, re.I):
        return "iim_abc"
    if re.search(IIM_ANY, seg, re.I):
        return "iim_other"
    if re.search(ISB, seg, re.I):
        return "isb"
    if re.search(ELITE_FOREIGN_BS, seg, re.I):
        return "elite_foreign"
    if re.search(TOP_INDIAN_BS, seg, re.I):
        return "top_indian_other"
    return "other"


def mba_class(desc):
    """Classify every MBA-like degree in a founder description."""
    classes = set()
    for m in re.finditer(MBA_TOKEN, desc, re.I):
        seg = segment_before(desc, m.start())
        if re.search(EXEC, desc[m.start() - 40:m.end() + 15], re.I):
            classes.add("exec")
            continue
        classes.add(classify_school(seg))
    # IIM / ISB entries written without a degree token, e.g. "Indian Institute of Management, Calcutta, 2010"
    for m in re.finditer(IIM_ANY + "|" + ISB, desc, re.I):
        window = desc[m.start():m.start() + 60]
        before = desc[max(0, m.start() - 6):m.start()]
        entry = re.split(r"(?:19|20)\d\d\b|\||\.\s|;", window)[0]
        if re.search(r"ex-?\s*$|ex\s*-\s*$", before, re.I) or re.search(MBA_TOKEN, entry, re.I):
            continue
        if re.search(r"\b(IPM|BBA|Integrated|Executive|MDP|EPGP|ePGP|PGPX|Faculty|Professor|Incubat|DLabs|Ventures|Foundation|Nagpur ,)", entry, re.I):
            continue
        classes.add(classify_school(entry))
    return classes


def edu_part(desc):
    # Tracxn writes "<career>. <education>"; employers sit before the last '. ' block
    return desc


def founder_flags(p):
    d = p["desc"]
    m = mba_class(d)
    role = p["role"]
    return {
        "any_mba": bool(m - {"exec"}),
        "mba_iim_abc": "iim_abc" in m,
        "mba_iim_other": "iim_other" in m,
        "mba_isb": "isb" in m,
        "mba_elite_foreign": "elite_foreign" in m,
        "mba_top_indian_other": "top_indian_other" in m,
        "mba_other": "other" in m,
        "mba_exec": "exec" in m,
        "iit": bool(re.search(IIT, d)),
        "top_ug_non_iit": bool(re.search(TOP_UG_NON_IIT, d, re.I)),
        "elite_foreign_uni": bool(re.search(ELITE_FOREIGN_UNI, d)),
        "eng_degree": bool(re.search(ENG, d)),
        "phd": bool(re.search(PHD, d)),
        "ca": bool(re.search(CA, d)),
        "ex_t1_vc": bool(re.search(T1_STAFF, d, re.I)),
        "ex_vc_pe": bool(re.search(VCPE, d, re.I)),
        "ex_big_tech": bool(re.search(BIGTECH, d, re.I)),
        "ex_unicorn": bool(re.search(UNICORN, d, re.I)),
        "ex_mbb": bool(re.search(MBB, d, re.I)),
        "ex_ibank": bool(re.search(IBANK, d, re.I)),
        "ex_founder_text": bool(re.search(r"ex-?\s?(co-?)?founder|founded|serial entrepreneur", d, re.I)),
        "technical_role": bool(re.search(r"\bCTO\b|technology|engineering|tech lead|chief technical", role, re.I)),
        "has_desc": len(d) > 5,
    }


def city_bucket(c):
    c = str(c).lower()
    if "bengaluru" in c or "bangalore" in c:
        return "bengaluru"
    if c in ("mumbai", "navi mumbai", "thane"):
        return "mumbai"
    if c in ("new delhi", "delhi", "gurugram", "gurgaon", "noida", "greater noida", "faridabad", "ghaziabad"):
        return "delhi_ncr"
    if c in ("pune", "hyderabad", "chennai"):
        return c
    return "other"


def build():
    r = pd.read_pickle(D + "rounds.pkl")
    inv = pd.read_pickle(D + "inv.pkl")
    c = pd.read_pickle(D + "companies.pkl")

    r["date"] = pd.to_datetime(r["Round Date"], errors="coerce")
    inv["date"] = pd.to_datetime(inv["Round Date"], errors="coerce")
    if PERIOD != "all":
        y0, y1 = map(int, PERIOD.split("-"))
        r = r[r.date.dt.year.between(y0, y1)]
        inv = inv[inv.date.dt.year.between(y0, y1)]
        c = c[c["Domain Name"].isin(set(r["Domain Name"]))]
    inv["is_t1"] = inv["Investor Name"].astype(str).str.strip().str.contains(T1RE)
    inv["is_lead"] = inv["Is Lead Investor"].astype(str).str.lower().eq("yes")
    led = inv[inv.is_t1 & inv.is_lead].groupby("Domain Name").size()
    part = inv[inv.is_t1].groupby("Domain Name").size()
    any_lead_info = inv[inv.is_lead].groupby("Domain Name").size()

    first = r.sort_values("date").groupby("Domain Name").first()
    rows = []
    for _, co in c.iterrows():
        dom = co["Domain Name"]
        people = [p for p in parse_people(co.get("Key People Info")) if re.search(r"founder", p["role"], re.I)]
        if not people:
            continue
        fl = [founder_flags(p) for p in people]
        row = {k: any(f[k] for f in fl) for k in fl[0]}
        tb = str(co.get("Team Background") or "")
        fh = str(co.get("Founder Highlights") or "")
        # Tracxn's own curated tags fill gaps in the free text
        row["iit"] |= bool(re.search(IIT, tb))
        row["ex_mbb"] |= bool(re.search(MBB, tb, re.I))
        row["ex_big_tech"] |= bool(re.search(BIGTECH, tb, re.I))
        row["ex_unicorn"] |= bool(re.search(UNICORN, tb, re.I))
        row["ex_ibank"] |= bool(re.search(IBANK, tb, re.I))
        row["ex_vc_pe"] |= "Ex-VC" in tb or row["ex_t1_vc"]
        row["repeat_founder"] = "Serial Founder" in fh or "Serial Entrepreneur" in tb or row.pop("ex_founder_text")
        row["prior_funded_founder"] = "Prior Funding" in fh
        row["prior_exit"] = bool(re.search(r"Prior Acquisition|Prior IPO", fh))
        row["prior_yc"] = "Prior YC" in fh
        row["mba_elite_any"] = row["mba_iim_abc"] or row["mba_isb"] or row["mba_elite_foreign"]
        row["solo_founder"] = len(people) == 1
        row["three_plus_founders"] = len(people) >= 3
        row["no_elite_credential"] = not (row["iit"] or row["top_ug_non_iit"] or row["elite_foreign_uni"]
                                          or row["mba_iim_abc"] or row["mba_isb"] or row["mba_iim_other"])
        f = first.loc[dom] if dom in first.index else None
        row.update({
            "company": co["Company Name"], "domain": dom,
            "n_founders": len(people),
            "frac_desc": np.mean([x["has_desc"] for x in fl]),
            "t1_lead": dom in led.index,
            "t1_any": dom in part.index,
            "lead_info": dom in any_lead_info.index,
            "year": str(f["date"].year) if f is not None and pd.notna(f["date"]) else "na",
            "sector": str(f["Practice Areas"]).split(",")[0].strip() if f is not None else "na",
            "founded": pd.to_numeric(co.get("Founded Year"), errors="coerce"),
            "city": city_bucket(co.get("City")),
            "stage_now": co.get("Company Stage"),
            "total_funding": pd.to_numeric(co.get("Total Funding (USD)"), errors="coerce"),
        })
        rows.append(row)
    df = pd.DataFrame(rows)
    df["founded_bkt"] = pd.cut(df["founded"], [0, 2014, 2017, 2019, 2021, 2030],
                               labels=["<=2014", "2015-17", "2018-19", "2020-21", "2022+"]).astype(str)
    return df


SIGNALS = [
    # (key, label, group)
    ("ex_t1_vc", "Ex tier-1 VC staff", "VC network"),
    ("ex_vc_pe", "Ex-VC / PE (any fund)", "VC network"),
    ("prior_funded_founder", "Founded a funded co. before", "Track record"),
    ("prior_exit", "Prior exit (acq. / IPO)", "Track record"),
    ("repeat_founder", "Repeat founder", "Track record"),
    ("prior_yc", "Prior YC-backed founder", "Track record"),
    ("ex_unicorn", "Ex-Indian unicorn", "Employer"),
    ("ex_big_tech", "Ex-Big Tech", "Employer"),
    ("ex_mbb", "Ex-McKinsey / BCG / Bain", "Employer"),
    ("ex_ibank", "Ex-investment bank", "Employer"),
    ("iit", "IIT", "College"),
    ("top_ug_non_iit", "BITS / NIT / IIIT / IISc etc.", "College"),
    ("elite_foreign_uni", "Elite foreign university", "College"),
    ("eng_degree", "Engineering / CS degree", "College"),
    ("phd", "PhD", "College"),
    ("ca", "Chartered Accountant", "College"),
    ("any_mba", "Any MBA", "MBA"),
    ("mba_iim_abc", "MBA: IIM A / B / C", "MBA"),
    ("mba_iim_other", "MBA: other IIMs", "MBA"),
    ("mba_isb", "MBA: ISB", "MBA"),
    ("mba_elite_foreign", "MBA: HBS / Stanford / Wharton / INSEAD etc.", "MBA"),
    ("mba_top_indian_other", "MBA: XLRI / FMS / SPJIMR / MDI etc.", "MBA"),
    ("mba_other", "MBA: everywhere else", "MBA"),
    ("mba_exec", "Executive / online MBA", "MBA"),
    ("technical_role", "Technical co-founder (CTO)", "Team"),
    ("solo_founder", "Solo founder", "Team"),
    ("three_plus_founders", "3+ founders", "Team"),
    ("no_elite_credential", "No elite credential at all", "Team"),
]
# signals that are nested in others are fitted in their own model (swap-in) to avoid collinearity
NESTED = {"any_mba": ["mba_iim_abc", "mba_iim_other", "mba_isb", "mba_elite_foreign", "mba_top_indian_other", "mba_other"],
          "ex_vc_pe": ["ex_t1_vc"], "repeat_founder": ["prior_funded_founder", "prior_exit"],
          "no_elite_credential": ["iit", "top_ug_non_iit", "elite_foreign_uni", "mba_iim_abc", "mba_isb", "mba_iim_other"]}
CORE = [k for k, _, _ in SIGNALS if k not in NESTED]


def design(df, sigs):
    X = df[sigs].astype(float)
    sec = df["sector"].where(df["sector"].map(df["sector"].value_counts()) >= 60, "other")
    ctrl = pd.get_dummies(pd.DataFrame({"year": df.year, "sec": sec, "city": df.city, "fy": df.founded_bkt}),
                          drop_first=True).astype(float)
    return sm.add_constant(X.join(ctrl))


def fit(df, sigs, outcome):
    m = sm.Logit(df[outcome].astype(float), design(df, sigs)).fit(disp=0, maxiter=300, method="bfgs")
    return m


def run(df, outcome):
    res = {}
    m = fit(df, CORE, outcome)
    for k in CORE:
        res[k] = (m.params[k], m.bse[k], m.pvalues[k])
    for k, kids in NESTED.items():
        sigs = [s for s in CORE if s not in kids] + [k]
        mm = fit(df, sigs, outcome)
        res[k] = (mm.params[k], mm.bse[k], mm.pvalues[k])
    rows = []
    for k, label, grp in SIGNALS:
        b, se, p = res[k]
        n = int(df[k].sum())
        if n < 25:  # Deedy's rule: at least 25 companies with the attribute
            continue
        rows.append(dict(signal=k, label=label, group=grp, n=n,
                         rate_with=df.loc[df[k], outcome].mean(), rate_without=df.loc[~df[k], outcome].mean(),
                         odds_ratio=np.exp(b), lo=np.exp(b - 1.96 * se), hi=np.exp(b + 1.96 * se), p=p))
    out = pd.DataFrame(rows)
    out["q"] = multipletests(out["p"], method="fdr_bh")[1]
    return out


def main():
    df = build()
    # keep companies where Tracxn actually describes the founders
    df = df[df.frac_desc > 0].copy()
    df.to_csv(f"{OUT}/dataset_tracxn{TAG}.csv", index=False)
    meta = dict(companies=len(df), founders=int(df.n_founders.sum()), t1_lead=int(df.t1_lead.sum()),
                t1_lead_rate=float(df.t1_lead.mean()), t1_any=int(df.t1_any.sum()),
                lead_info_rate=float(df.lead_info.mean()), years=df.year.value_counts().to_dict())
    print(json.dumps(meta, indent=1))
    pd.set_option("display.width", 220)
    allres = {}
    for outcome in ["t1_lead", "t1_any"]:
        res = run(df, outcome)
        res.to_csv(f"{OUT}/results_{outcome}{TAG}.csv", index=False)
        allres[outcome] = res
        print(f"\n=== {outcome} ===")
        print(res.round(3).to_string(index=False))
    # sensitivity: only companies with lead-investor info at all
    sub = df[df.lead_info]
    res = run(sub, "t1_lead"); res.to_csv(f"{OUT}/results_t1_lead_leadinfo_only{TAG}.csv", index=False)
    print(f"\n=== t1_lead, lead-info subset n={len(sub)} ===")
    print(res[["label", "n", "odds_ratio", "lo", "hi", "q"]].round(3).to_string(index=False))
    json.dump(meta, open(f"{OUT}/meta{TAG}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
