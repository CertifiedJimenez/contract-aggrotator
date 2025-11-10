from .base import BaseClient
from bs4 import BeautifulSoup
from datetime import datetime

class CWJobsScraper(BaseClient):
    BASE_URL = "https://www.cwjobs.co.uk/jobs/django-contract/in-london?radius=30&searchOrigin=Resultlist_top-search"

    def fetch(self):
        result = self._request("request.get", self.BASE_URL, maxTimeout=60000)
        html_text = result.get("solution", {}).get("response", "") if isinstance(result, dict) else result
        return html_text

    def parse(self, html_text):
        soup = BeautifulSoup(html_text, "html.parser")
        jobs = []
        for card in soup.select("article[data-testid='job-item']"):
            title = (card.select_one("[data-testid='job-item-title']") or {}).get_text(strip=True)
            company = (card.select_one("[data-at='job-item-company-name']") or {}).get_text(strip=True)
            location = (card.select_one("[data-at='job-item-location']") or {}).get_text(strip=True)
            salary = (card.select_one("[data-at='job-item-salary-info']") or {}).get_text(strip=True)
            description = (card.select_one("[data-at='jobcard-content']") or {}).get_text(" ", strip=True)
            posted = (card.select_one("[data-at='job-item-timeago']") or {}).get_text(strip=True)
            link_tag = card.select_one("a[data-at=job-item-title]")
            url = f"https://www.cwjobs.co.uk{link_tag['href']}" if link_tag and link_tag.has_attr("href") else ""
            jobs.append({
                "company": company,
                "title": title,
                "description": description,
                "url": url,
                "posted": posted,
                "salary": salary,
                "location": location,
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
        print(f"[✓] Inserted {len(jobs)} CWJobs records")