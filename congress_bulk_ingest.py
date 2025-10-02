###############################################################################
# Name:        Congress Bulk Data Ingest Script
# Date:        2025-10-01
# Script Name: congress_bulk_ingest.py
# Version:     1.0
# Log Summary: Initial version for ingesting and parsing bulk legislative data
# Description: Ingests US Congress bulk data (bills, votes, members, sessions)
#              from official sources supported by unitedstates/congress repo.
# Change Summary:
#   - 1.0: First release. Supports download, extraction, parsing, logging.
# Inputs:
#   - BULK_DATA_URLS: List of URLs to official bulk data zips/tarballs.
#   - OUTPUT_DIR: Directory for storing and extracting bulk data.
# Outputs:
#   - Prints summary of ingested bills, votes, sessions, members.
#   - Extracted files in OUTPUT_DIR.
###############################################################################

import os
import requests
import zipfile
import tarfile
import glob
import json
import xml.etree.ElementTree as ET

# ---------------- CONFIGURABLE VARIABLES ---------------- #
BULK_DATA_URLS = [
    # Bills (Congress.gov official bulk data)
    "https://www.govinfo.gov/bulkdata/BILLSTATUS/118/hr/BILLSTATUS-118hr.zip",
    # Senate votes (example)
    "https://www.govinfo.gov/bulkdata/ROLLCALLVOTE/118/senate/ROLLCALLVOTE-118-senate.zip",
    # House votes (example)
    "https://www.govinfo.gov/bulkdata/ROLLCALLVOTE/118/house/ROLLCALLVOTE-118-house.zip",
    # Members (example - from unitedstates/congress repo)
    "https://theunitedstates.io/congress-legislators/legislators-current.json",
    # Add other relevant bulk data URLs here...
]
OUTPUT_DIR = "./bulk_data"

# ------------------ UTILITY FUNCTIONS ------------------- #
def log(msg):
    print("[LOG]", msg)

def download_file(url, dest):
    log(f"Downloading {url} ...")
    resp = requests.get(url, stream=True)
    if resp.status_code == 200:
        with open(dest, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        log(f"Downloaded to {dest}")
    else:
        log(f"Failed to download {url} (status {resp.status_code})")

def extract_zip(zip_path, extract_to):
    log(f"Extracting {zip_path} ...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    log(f"Extracted to {extract_to}")

def extract_tar(tar_path, extract_to):
    log(f"Extracting {tar_path} ...")
    with tarfile.open(tar_path, 'r:*') as tar_ref:
        tar_ref.extractall(extract_to)
    log(f"Extracted to {extract_to}")

def parse_bill_xml(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        bill_id = root.findtext('.//billNumber')
        title = root.findtext('.//title')
        sponsor = root.findtext('.//sponsor//fullName')
        return {
            "bill_id": bill_id,
            "title": title,
            "sponsor": sponsor
        }
    except Exception as e:
        log(f"Error parsing {xml_file}: {e}")
        return None

def parse_vote_xml(xml_file):
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        vote_id = root.findtext('.//vote_id')
        result = root.findtext('.//result')
        yeas = root.findtext('.//yeas')
        nays = root.findtext('.//nays')
        return {
            "vote_id": vote_id,
            "result": result,
            "yeas": yeas,
            "nays": nays
        }
    except Exception as e:
        log(f"Error parsing {xml_file}: {e}")
        return None

def parse_member_json(json_file):
    members = []
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            for member in data:
                name = member.get("name", {}).get("official_full", "")
                id = member.get("id", {}).get("bioguide", "")
                party = member.get("terms", [{}])[-1].get("party", "")
                state = member.get("terms", [{}])[-1].get("state", "")
                members.append({"name": name, "bioguide_id": id, "party": party, "state": state})
    except Exception as e:
        log(f"Error parsing {json_file}: {e}")
    return members

def summarize_data(output_dir):
    bill_files = glob.glob(os.path.join(output_dir, "**", "*.xml"), recursive=True)
    vote_files = glob.glob(os.path.join(output_dir, "**", "*votes*.xml"), recursive=True)
    member_files = glob.glob(os.path.join(output_dir, "*.json"))

    log(f"Found {len(bill_files)} bill XML files.")
    log(f"Found {len(vote_files)} vote XML files.")
    log(f"Found {len(member_files)} member JSON files.")

    bills = [parse_bill_xml(f) for f in bill_files[:20]]  # Sample first 20
    votes = [parse_vote_xml(f) for f in vote_files[:20]]  # Sample first 20

    members = []
    for jf in member_files:
        members.extend(parse_member_json(jf))

    print("\n--- Bills Sample ---")
    for b in bills:
        if b:
            print(b)
    print("\n--- Votes Sample ---")
    for v in votes:
        if v:
            print(v)
    print("\n--- Members Sample ---")
    for m in members[:20]:
        print(m)

# --------------------- MAIN SCRIPT ---------------------- #
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for url in BULK_DATA_URLS:
        filename = url.split("/")[-1]
        dest_path = os.path.join(OUTPUT_DIR, filename)

        # Download file or skip if already present
        if not os.path.exists(dest_path):
            download_file(url, dest_path)
        else:
            log(f"File already exists: {dest_path}")

        # Extract if archive
        if filename.endswith(".zip"):
            extract_zip(dest_path, OUTPUT_DIR)
        elif filename.endswith((".tar.gz", ".tgz", ".tar")):
            extract_tar(dest_path, OUTPUT_DIR)
        # If JSON, do nothing

    # Summarize what's been ingested
    summarize_data(OUTPUT_DIR)

if __name__ == "__main__":
    main()

###############################################################################
# USAGE:
#   1. Install dependencies: pip install requests
#   2. Update BULK_DATA_URLS with additional sources if desired.
#   3. Run: python congress_bulk_ingest.py
#   4. Output will show sample bills, votes, members.
# NOTES:
#   - For full ingestion, expand file parsing logic as needed.
#   - For OpenStates, Data.gov, or other sources, add their bulk data URLs.
###############################################################################