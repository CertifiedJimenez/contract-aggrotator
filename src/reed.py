from .base import BaseClient
from bs4 import BeautifulSoup
from datetime import datetime
import time


class ReedScraper(BaseClient):
    BASE_TEMPLATE = "https://www.reed.co.uk/jobs/{query}-jobs-in-{location}?pageno={page}"

    def __init__(self, query="django-contractor", location="london", pages=2):
        super().__init__()
        self.query = query
        self.location = location
        self.pages = pages

    def build_urls(self):
        return [self.BASE_TEMPLATE.format(query=self.query, location=self.location, page=p) for p in range(1, self.pages + 1)]

    def fetch_all(self):
        pages = []
        for url in self.build_urls():
            result = self._request("request.get", url, maxTimeout=60000)
            html_text = result.get("solution", {}).get("response", "") if isinstance(result, dict) else result
            pages.append(html_text)
        return pages

    def fetch_detail(self, url):
        """Fetch full job description from a Reed job page."""
        try:
            result = self._request("request.get", url, maxTimeout=60000)
            html_text = result.get("solution", {}).get("response", "") if isinstance(result, dict) else result
            soup = BeautifulSoup(html_text, "html.parser")
            desc_el = soup.select_one('[data-qa="job-description"]')
            return desc_el.get_text(" ", strip=True) if desc_el else ""
        except Exception as e:
            print(f"[!] Failed to fetch detail for {url}: {e}")
            return ""

    def parse(self, html_text):
        soup = BeautifulSoup(html_text, "html.parser")
        jobs = []
        for card in soup.select("article.card.job-card_jobCard__MkcJD"):
            title_el = card.select_one("h2.job-card_jobResultHeading__title__IQ8iT a")
            company_el = card.select_one("div.job-card_jobResultHeading__postedBy__sK_25 a")
            desc_el = card.select_one("button.job-card_btnToggleJobDescription__C8fds")
            url = f"https://www.reed.co.uk{title_el['href']}" if title_el and title_el.get("href") else ""

            short_desc = desc_el.get_text(strip=True) if desc_el else ""
            full_desc = self.fetch_detail(url) if url else ""

            jobs.append({
                "company": company_el.get_text(strip=True) if company_el else "",
                "title": title_el.get_text(strip=True) if title_el else "",
                "description": full_desc or short_desc,
                "url": url,
                "posted": "",
            })

            # brief delay to be kind to the server
            time.sleep(0.5)

        return jobs

    def run(self):
        all_pages = self.fetch_all()
        total = 0
        for html_text in all_pages:
            jobs = self.parse(html_text)
            total += len(jobs)
            for job in jobs:
                self.insert_job(
                    company=job["company"],
                    title=job["title"],
                    description=job["description"],
                    link=job["url"],
                    date_posted=datetime.utcnow(),
                )
        print(f"[✓] Inserted {total} Reed records")