import time
from src import cvlibrary, cwjobs, jobserve, reed, indeed


def run_all():
    start = time.time()
    print("🚀 Starting job scraper pipeline...\n")

    scrapers = [
        ("CVLibrary", cvlibrary.CVLibraryScraper),
        ("CWJobs", cwjobs.CWJobsScraper),
        ("JobServe", jobserve.JobServeScraper),
        ("Reed", reed.ReedScraper),
        ("Indeed", indeed.IndeedScraper)
    ]

    total_inserted = 0

    for name, ScraperClass in scrapers:
        print(f"\n--- Running {name} ---")
        try:
            scraper = ScraperClass()
            scraper.run()
            total_inserted += 1
        except Exception as e:
            print(f"[!] {name} failed: {e}")

    print(f"\n✅ All scrapers finished in {time.time() - start:.2f}s")
    print(f"Total sources processed: {total_inserted}")


if __name__ == "__main__":
    run_all()