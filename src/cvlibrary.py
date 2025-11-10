from .base import BaseClient
from bs4 import BeautifulSoup
from datetime import datetime

class CVLibraryScraper(BaseClient):
    BASE_URL = "https://www.cv-library.co.uk/django-contractor-jobs?us=1"

    def fetch(self):
        result = self._request("request.get", self.BASE_URL, maxTimeout=60000)
        html_text = result.get("solution", {}).get("response", "") if isinstance(result, dict) else result
        return html_text

    def parse(self, html_text):
        soup = BeautifulSoup(html_text, "html.parser")
        jobs = []
        for card in soup.select("article.job.search-card"):
            title_el = card.select_one("h2.job__title a")
            company_el = card.select_one(".job__posted-by a")
            desc_el = card.select_one(".job__description")
            posted_el = card.select_one(".job__posted-by span.color-green")

            url = f"https://www.cv-library.co.uk{title_el['href']}" if title_el and title_el.get("href") else ""
            jobs.append({
                "company": company_el.get_text(strip=True) if company_el else "",
                "title": title_el.get_text(strip=True) if title_el else "",
                "description": desc_el.get_text(" ", strip=True) if desc_el else "",
                "url": url,
                "posted": posted_el.get_text(strip=True) if posted_el else "",
            })
        return jobs

    def run(self):
        html_text = self.fetch()
        jobs = self.parse(html_text)
        for job in jobs:
            self.insert_job(
                company=job["company"],
                title=job["title"],
                description=job["description"],
                link=job["url"],
                date_posted=datetime.utcnow(),
            )
        print(f"[✓] Inserted {len(jobs)} CVLibrary records")