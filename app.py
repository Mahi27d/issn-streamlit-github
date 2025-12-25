import streamlit as st
import csv
import requests
import time
import os

# ---------------- CONFIG ----------------
ROWS_PER_ISSN = 50          # Reduced for Streamlit Cloud safety
MAX_ROWS_PER_FILE = 200_000 # Smaller files for browser download
SLEEP = 1
HEADERS = {"User-Agent": "ISSN-Streamlit-GitHub/1.0"}

st.set_page_config(page_title="ISSN Metadata Extractor", layout="wide")

st.title("ISSN Metadata Extractor (GitHub Only)")
st.info("Runs fully on GitHub Streamlit Cloud")

year = st.number_input("Select Year", value=2025, min_value=1900, max_value=2100)

uploaded_file = st.file_uploader(
    "Upload ISSN CSV (column name must be 'issn')",
    type=["csv"]
)

run = st.button("Run Extraction")

def fetch_articles(issn, year, month):
    url = "https://api.crossref.org/works"
    params = {
        "filter": f"issn:{issn},from-pub-date:{year}-{month:02d}-01,until-pub-date:{year}-{month:02d}-31",
        "rows": ROWS_PER_ISSN
    }
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    if r.status_code == 200:
        return r.json()["message"]["items"]
    return []

if run and uploaded_file:

    issns = []
    reader = csv.DictReader(uploaded_file.getvalue().decode("utf-8").splitlines())
    for row in reader:
        issns.append(row["issn"])

    st.success(f"Loaded {len(issns)} ISSNs")

    os.makedirs("output", exist_ok=True)

    progress = st.progress(0)
    total_steps = len(issns) * 12
    done = 0

    generated_files = []

    for month in range(1, 13):
        month_str = f"{year}-{month:02d}"
        part = 1
        row_count = 0

        def new_file(part):
            filename = f"output/issn_{month_str}_part{part}.csv"
            f = open(filename, "w", newline="", encoding="utf-8")
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "Year","Month","ISSN","DOI","Article Title",
                    "Volume","Issue","Page",
                    "Journal Title","Publisher"
                ]
            )
            writer.writeheader()
            return f, writer, filename

        file, writer, current_file = new_file(part)
        generated_files.append(current_file)

        for issn in issns:
            articles = fetch_articles(issn, year, month)

            for art in articles:
                if row_count >= MAX_ROWS_PER_FILE:
                    file.close()
                    part += 1
                    row_count = 0
                    file, writer, current_file = new_file(part)
                    generated_files.append(current_file)

                writer.writerow({
                    "Year": year,
                    "Month": month_str,
                    "ISSN": issn,
                    "DOI": art.get("DOI"),
                    "Article Title": art.get("title", [""])[0],
                    "Volume": art.get("volume"),
                    "Issue": art.get("issue"),
                    "Page": art.get("page"),
                    "Journal Title": art.get("container-title", [""])[0],
                    "Publisher": art.get("publisher")
                })
                row_count += 1

            time.sleep(SLEEP)
            done += 1
            progress.progress(done / total_steps)

        file.close()

    st.success("Extraction completed")

    st.subheader("Download CSV files")
    for f in generated_files:
        with open(f, "rb") as file:
            st.download_button(
                label=f"Download {os.path.basename(f)}",
                data=file,
                file_name=os.path.basename(f),
                mime="text/csv"
            )
