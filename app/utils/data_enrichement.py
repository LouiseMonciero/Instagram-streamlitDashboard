import time
import math
from typing import Dict, Any, Optional, Iterable
import requests
import pandas as pd


# ------------- HTTP utils (shared session + retry/backoff) -------------------
_session = requests.Session()
_session.headers.update(UA)

RETRYABLE = {429, 500, 502, 503, 504}

def _json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    retries: int = 3,
    timeout: int = 20,
) -> Any:
    hdrs = {**(_session.headers or {}), **(headers or {})}
    for k in range(retries):
        r = _session.get(url, params=params, headers=hdrs, timeout=timeout)
        if r.status_code in RETRYABLE:
            # exponential-ish backoff
            time.sleep(1.2 * (k + 1))
            continue
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            raise RuntimeError(f"Non-JSON from {url} (status {r.status_code})")
    raise RuntimeError(f"Failed after {retries} attempts: {url}")

# ------------- Providers -----------------------------------------------------
# (simple in-memory caches to avoid repeated calls on same names/qids)
_cache_qid: Dict[str, Optional[str]] = {}
_cache_props: Dict[str, Dict[str, Any]] = {}
_cache_domain: Dict[str, Optional[str]] = {}
_cache_oc_country: Dict[str, Optional[str]] = {}

def wikipedia_qid(name: str, langs: Iterable[str] = WIKIPEDIA_LANGS) -> Optional[str]:
    """Find best Wikipedia page then return its Wikidata QID."""
    key = f"{name}|{'-'.join(langs)}"
    if key in _cache_qid:
        return _cache_qid[key]
    for lang in langs:
        data = _json(
            f"https://{lang}.wikipedia.org/w/api.php",
            {"action": "query", "list": "search", "srsearch": name, "srlimit": 1, "format": "json"},
        )
        hits = data.get("query", {}).get("search", [])
        if not hits:
            continue
        title = hits[0]["title"]
        data2 = _json(
            f"https://{lang}.wikipedia.org/w/api.php",
            {"action": "query", "titles": title, "prop": "pageprops", "format": "json"},
        )
        pages = data2.get("query", {}).get("pages", {})
        for _, p in pages.items():
            qid = p.get("pageprops", {}).get("wikibase_item")
            if qid:
                _cache_qid[key] = qid
                time.sleep(REQUEST_PAUSE)
                return qid
        time.sleep(REQUEST_PAUSE)
    _cache_qid[key] = None
    return None

def wikidata_props(qid: str) -> Dict[str, Any]:
    """Return selected props for a Wikidata entity."""
    if qid in _cache_props:
        return _cache_props[qid]
    sparql = f"""
    SELECT ?countryLabel ?industryLabel ?hqLabel ?inception ?website WHERE {{
      VALUES ?c {{ wd:{qid} }}
      OPTIONAL {{ ?c wdt:P17  ?country.   }}
      OPTIONAL {{ ?c wdt:P452 ?industry.  }}
      OPTIONAL {{ ?c wdt:P159 ?hq.        }}
      OPTIONAL {{ ?c wdt:P571 ?inception. }}
      OPTIONAL {{ ?c wdt:P856 ?website.   }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en,fr". }}
    }}
    """
    js = _json(
        "https://query.wikidata.org/sparql",
        params={"query": sparql},
        headers={"Accept": "application/sparql-results+json"},
        timeout=25,
    )
    rows = js.get("results", {}).get("bindings", [])
    if not rows:
        _cache_props[qid] = {}
        return {}
    r = rows[0]
    getv = lambda k: r[k]["value"] if k in r else None
    out = {
        "country": getv("countryLabel"),
        "industry": getv("industryLabel"),
        "hq_location": getv("hqLabel"),
        "inception": getv("inception"),
        "website": getv("website"),
    }
    _cache_props[qid] = out
    time.sleep(REQUEST_PAUSE)
    return out

def clearbit_domain(name: str) -> Optional[str]:
    """Clearbit autocomplete to guess website from company name."""
    if name in _cache_domain:
        return _cache_domain[name]
    js = _json(
        "https://autocomplete.clearbit.com/v1/companies/suggest",
        params={"query": name},
    )
    dom = js[0].get("domain") if js else None
    out = f"https://{dom}" if dom else None
    _cache_domain[name] = out
    time.sleep(REQUEST_PAUSE)
    return out

def opencorporates_country(name: str) -> Optional[str]:
    """Get country via OpenCorporates (jurisdiction or registered address)."""
    if name in _cache_oc_country:
        return _cache_oc_country[name]
    js = _json(
        "https://api.opencorporates.com/v0.4/companies/search",
        params={"q": name, "per_page": 1},
    )
    comps = js.get("results", {}).get("companies", [])
    if not comps:
        _cache_oc_country[name] = None
        return None
    c = comps[0].get("company", {})
    juris = c.get("jurisdiction_code")
    if juris and juris[:2] in JURIS_MAP:
        out = JURIS_MAP[juris[:2]]
        _cache_oc_country[name] = out
        time.sleep(REQUEST_PAUSE)
        return out
    addr = c.get("registered_address", {})
    if isinstance(addr, dict) and addr.get("country"):
        out = addr.get("country")
        _cache_oc_country[name] = out
        time.sleep(REQUEST_PAUSE)
        return out
    _cache_oc_country[name] = None
    return None

# ------------- Row-level backfill -------------------------------------------
NEEDED_COLS = ["qid", "country", "industry", "hq_location", "inception", "website"]

def backfill_from_services(row: pd.Series, name_col: str) -> Dict[str, Any]:
    """
    Given a row, try to fill missing NEEDED_COLS using providers.
    Returns a dict of {col: new_value, ...} for what changed.
    """
    out: Dict[str, Any] = {}
    name = (row.get(name_col) or "").strip()
    if not name:
        return out

    # QID (then Wikidata props)
    if pd.isna(row.get("qid")) or not str(row.get("qid")).strip():
        q = wikipedia_qid(name)
        if not q:
            # try other order if needed
            q = wikipedia_qid(name, langs=reversed(WIKIPEDIA_LANGS))
        if q:
            out["qid"] = q
            props = wikidata_props(q)
            for k, v in props.items():
                if k in NEEDED_COLS and (pd.isna(row.get(k)) or not str(row.get(k)).strip()) and v:
                    out[k] = v

    # Website from Clearbit (only if still missing or not set by Wikidata)
    if (pd.isna(row.get("website")) or not str(row.get("website")).strip()):
        w = clearbit_domain(name)
        if w:
            out.setdefault("website", w)

    # Country from OpenCorporates (if still missing)
    if (pd.isna(row.get("country")) or not str(row.get("country")).strip()):
        co = opencorporates_country(name)
        if co:
            out.setdefault("country", co)

    return out

# ------------- Public function ----------------------------------------------
def enrich_companies(
    df: pd.DataFrame,
    name_col: str = "advertiser_name",
    pause: float = REQUEST_PAUSE,
    save_every: Optional[int] = 100,
    save_path: str = "enriched_partial.csv",
    only_if_missing: bool = True,
) -> pd.DataFrame:
    """
    Enrich a DataFrame in-place and return it.

    Parameters
    ----------
    df : DataFrame
        Your input DataFrame (must contain `name_col`).
    name_col : str
        Column with company names (defaults to 'advertiser_name').
    pause : float
        Sleep between external requests (politeness).
    save_every : int or None
        If set, saves a partial CSV every N processed rows.
    save_path : str
        Path for partial saves.
    only_if_missing : bool
        If True, process only rows where at least one of NEEDED_COLS is missing.

    Returns
    -------
    DataFrame (same object, enriched in place)
    """

    if name_col not in df.columns:
        raise KeyError(f"Missing column `{name_col}` in input DataFrame.")

    # Ensure target columns exist
    for c in NEEDED_COLS + ["enrich_error"]:
        if c not in df.columns:
            df[c] = pd.NA

    # Which rows to process
    if only_if_missing:
        mask = df[NEEDED_COLS].isna().any(axis=1)
        idxs = df.index[mask]
    else:
        idxs = df.index

    updated = 0
    for i, idx in enumerate(idxs, 1):
        try:
            changes = backfill_from_services(df.loc[idx], name_col=name_col)
            if changes:
                for k, v in changes.items():
                    df.at[idx, k] = v
                updated += 1
        except Exception as e:
            df.at[idx, "enrich_error"] = str(e)[:200]
        finally:
            # brief pause to avoid hammering APIs
            time.sleep(pause)

        if save_every and i % save_every == 0:
            try:
                df.to_csv(save_path, index=False)
            except Exception:
                pass  # best effort

    print(f"Rows updated: {updated} / {len(idxs)}")
    return df


# ---------------- Example usage ---------------------------------------------
# If your DataFrame is named `enriched` and the company name is in `advertiser_name`:
# enriched = enrich_companies(enriched, name_col="advertiser_name")
#
# If your DataFrame uses another name column (e.g., 'company'):
# enriched = enrich_companies(enriched, name_col="company")
