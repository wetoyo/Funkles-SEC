# scrape.py
import os
import json
from datetime import datetime, timedelta
import requests
from datamule import Index
import xml.etree.ElementTree as ET
from .scrape_utils import get_outstanding_shares
from .paths import CACHE_DIR, SETTINGS_PATH


def scrape():
    index = Index()
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)


    # SEC headers to avoid 403
    HEADERS = {
        "User-Agent": "weto yo (yonoweto@gmail.com)",  # SEC requires real contact info
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov"
    }

    ns = {
    "edgar": "http://www.sec.gov/edgar/schedule13D",
    "com": "http://www.sec.gov/edgar/common"
    }

    # Search for 13D filings
    # Load settings from settings.json
    with open(SETTINGS_PATH, "r") as f:
        settings = json.load(f)

    form_type_index = settings.get("form_type_index", 0)
    form_types = settings.get("form_type", ["SCHEDULE 13D"])
    form_type = form_types[form_type_index] if form_type_index < len(form_types) else form_types[0]

    date_range_days = settings.get("date_range_days", 7)
    cacherange = today - timedelta(days=date_range_days)

    results = index.search_submissions(
        filing_date=(yesterday, today),
        submission_type=form_type,
        requests_per_second=3
    )

    if not results:
        print("No filings found.")
        exit()

    for result in results:
        try:
            sec_id = result["_id"]  # e.g., "0001062993-25-015044:exhibit99-2.htm"
            accession, filename = sec_id.split(":")

            # Only XML files
            if not filename.lower().endswith(".xml"):
                continue

            ciks = result["_source"].get("ciks", [])
            if not ciks:
                print(f"No CIK found for {sec_id}, skipping.")
                continue
            cik = ciks[0].zfill(10)  # full 10-digit CIK for SEC URL

            # Format accession number for SEC URL
            accession_nodash = accession.replace("-", "")

            # Build SEC URL
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{filename}"

            # Fetch XML filing
            response = requests.get(url, headers=HEADERS)
            if response.status_code != 200:
                print(f"Failed to download {url} ({response.status_code})")
                continue

            # Save XML file, prefix with accession to avoid collisions
            safe_filename = f"{accession}_{filename}"
            file_path = os.path.join(CACHE_DIR, safe_filename)
            with open(file_path, "wb") as f:
                f.write(response.content)


            tree = ET.parse(file_path)
            root = tree.getroot()

            share_amount = None
            share_pct = None

            for info in root.findall(".//edgar:reportingPersonInfo", ns):

                agg = info.find("edgar:aggregateAmountOwned", ns)
                percent = info.find("edgar:percentOfClass", ns)

                share_amount = float(agg.text) if agg is not None else None
                share_pct = float(percent.text) if percent is not None else None

            oustanding_shares = get_outstanding_shares(cik)
            # Save metadata
            meta = {
                "filename": safe_filename,
                "path": file_path,
                "date": result["_source"].get("file_date", str(today)),
                "form": result["_source"].get("form"),
                "file_type": result["_source"].get("file_type"),
                "original_filename": filename,
                "accession": accession,
                "cik": cik,
                "label": None,
                "summary": None,
                "share %": share_amount / get_outstanding_shares(cik) if share_amount and oustanding_shares else None
            }
            meta_path = os.path.join(CACHE_DIR, f"{safe_filename}.meta.json")
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=4)

            print(f"Downloaded {safe_filename} from SEC")

        except Exception as e:
            print(f"Error processing {sec_id}: {e}")

    files_removed = 0
    # Optional cleanup for files older than 7 days
    for root, dirs, files in os.walk(CACHE_DIR):
        for file in files:
            if file.endswith(".meta.json"):
                meta_path = os.path.join(root, file)
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                file_date = datetime.strptime(meta["date"], "%Y-%m-%d").date()
                if file_date < cacherange:
                    os.remove(meta_path)
                    files_removed += 1
                    if os.path.exists(meta["path"]):
                        os.remove(meta["path"])
    return f'"Scrape Sucessful. {len(results)} saved to filing cache, {files_removed} old files removed."' 


