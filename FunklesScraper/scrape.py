import os
import json
from datetime import datetime, timedelta
import requests
from datamule import Index
import xml.etree.ElementTree as ET
from .scrape_utils import get_outstanding_shares, HEADERS
from .paths import CACHE_DIR

def scrape(form_type, days):
    try:
        index = Index()
    except Exception as e:
        print(f"Error initializing Index: {e}")
        return f"Error initializing Index: {e}"

    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    ns = {
        "edgar": "http://www.sec.gov/edgar/schedule13D",
        "com": "http://www.sec.gov/edgar/common"
    }
    date_range_days = days
    cacherange = today - timedelta(days=date_range_days)

    try:
        results = index.search_submissions(
            filing_date=(cacherange, today),
            submission_type=form_type,
            requests_per_second=3
        )
    except Exception as e:
        print(f"Error searching submissions: {e}")
        return f"Error searching submissions: {e}"

    if not results:
        print("No filings found.")
        return "No filings found."

    for result in results:
        try:
            sec_id = result["_id"]
            accession, filename = sec_id.split(":")
            if not filename.lower().endswith(".xml"):
                continue

            ciks = result["_source"].get("ciks", [])
            if not ciks:
                print(f"No CIK found for {sec_id}, skipping.")
                continue
            cik = ciks[0].zfill(10)
            accession_nodash = accession.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_nodash}/{filename}"

            # Fetch XML filing safely
            result_count = 0
            try:
                response = requests.get(url, headers=HEADERS, timeout=15)
                response.raise_for_status()
                result_count += 1
            except requests.RequestException as e:
                print(f"Failed to download {url}: {e}")
                result_count += -1
                continue

            safe_filename = f"{accession}_{filename}"
            file_path = os.path.join(CACHE_DIR, safe_filename)
            with open(file_path, "wb") as f:
                f.write(response.content)

            # Parse XML
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
            except Exception as e:
                print(f"Failed to parse XML {safe_filename}: {e}")
                continue

            # Extract issuer (company of interest)
            issuer_name = None
            try:
                issuer_elem = root.find(".//edgar:issuerName", ns)
                if issuer_elem is not None and issuer_elem.text:
                    issuer_name = issuer_elem.text.strip()
            except Exception as e:
                print(f"Failed to extract issuer from {safe_filename}: {e}")

            # Extract reporting persons (parties of interest)
            reporting_persons = []
            try:
                for rp in root.findall(".//edgar:reportingPersonName", ns):
                    if rp is not None and rp.text:
                        reporting_persons.append(rp.text.strip())
            except Exception as e:
                print(f"Failed to extract reporting persons from {safe_filename}: {e}")

            # Extract shares + percent
            share_amount = None
            for info in root.findall(".//edgar:reportingPersonInfo", ns):
                agg = info.find("edgar:aggregateAmountOwned", ns)
                share_amount = float(agg.text) if agg is not None else None

            oustanding_shares = get_outstanding_shares(cik)

            meta = {
                "filename": safe_filename,
                "path": file_path,
                "date": result["_source"].get("file_date", str(today)),
                "form": result["_source"].get("form"),
                "file_type": result["_source"].get("file_type"),
                "original_filename": filename,
                "issuer": issuer_name,
                "reporting_persons": reporting_persons,
                "cik": cik,
                "label": None,
                "summary": None,
                "share %": (share_amount / oustanding_shares if share_amount and oustanding_shares else None)
            }

            meta_path = os.path.join(CACHE_DIR, f"{safe_filename}.meta.json")
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=4)

            print(f"Downloaded {safe_filename} from SEC")

        except Exception as e:
            print(f"Error processing {sec_id}: {e}")

    # Optional cleanup
    files_removed = 0
    for root_dir, dirs, files in os.walk(CACHE_DIR):
        for file in files:
            if file.endswith(".meta.json"):
                meta_path = os.path.join(root_dir, file)
                try:
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                    file_date = datetime.strptime(meta["date"], "%Y-%m-%d").date()
                    if file_date < cacherange:
                        os.remove(meta_path)
                        files_removed += 1
                        if os.path.exists(meta["path"]):
                            os.remove(meta["path"])
                except Exception as e:
                    print(f"Error cleaning up {file}: {e}")

    return f'Scrape Successful. {result_count} saved to filing cache, {files_removed} old files removed.'
