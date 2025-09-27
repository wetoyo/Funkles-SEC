import requests

HEADERS = {
    "User-Agent": "weto yo (yonoweto@gmail.com)",  # SEC requires real contact info
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}

def get_outstanding_shares(cik: str):
    """
    Query SEC Company Facts API for most recent outstanding common shares.
    Returns None if unavailable or any error occurs.
    """
    cik = cik.zfill(10)  # SEC requires zero-padded CIK
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    headers = {"User-Agent": HEADERS["User-Agent"]}

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()  # Raises HTTPError for bad status codes
        data = r.json()
    except requests.RequestException as e:
        print(f"Failed to download {url}: {e}")
        return None
    except ValueError as e:
        print(f"Invalid JSON from SEC API for CIK {cik}: {e}")
        return None

    try:
        units = data["facts"]["dei"]["EntityCommonStockSharesOutstanding"]["units"]
        # Pick the most recent entry from any unit
        for unit_entries in units.values():
            latest = sorted(unit_entries, key=lambda x: x["end"], reverse=True)[0]
            return latest["val"]
    except Exception as e:
        print(f"No outstanding shares found for CIK {cik}: {e}")
        return None
