import requests

def get_outstanding_shares(cik: str):
    """
    Query SEC Company Facts API for most recent outstanding common shares.
    """
    cik = cik.zfill(10)  # SEC requires zero-padded CIK
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    headers = {"User-Agent": "myapp contact@example.com"}  # <- put real contact here
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        print(f"SEC API error for CIK {cik}: {r.status_code}")
        return None

    data = r.json()
    try:
        units = data["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]
        # Pick the most common unit (shares) and latest filing
        for unit, entries in units.items():
            latest = sorted(entries, key=lambda x: x["end"], reverse=True)[0]
            return latest["val"]
    except Exception as e:
        print(f"No outstanding shares found for {cik}: {e}")
    return None