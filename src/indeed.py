from .base import BaseClient
from bs4 import BeautifulSoup
from datetime import datetime
import html
import time


class IndeedScraper(BaseClient):
    BASE_URL = "https://uk.indeed.com/jobs?q=django&l=London&from=searchOnHP"

    def __init__(self):
        super().__init__()

    def fetch(self, page=0):
        params = {"q": "django", "l": "London", "start": page}
        result = self._request("request.get", self.BASE_URL, params=params, maxTimeout=60000)
        return result.get("solution", {}).get("response", "") if isinstance(result, dict) else result

    def fetch_detail(self, url):
        """Fetch full job description from job page."""
        try:
            result = self._request("request.get", url, maxTimeout=60000)
            html_text = result.get("solution", {}).get("response", "") if isinstance(result, dict) else result
            soup = BeautifulSoup(html.unescape(html_text), "html.parser")
            desc = soup.select_one("#jobDescriptionText")
            return desc.get_text(" ", strip=True) if desc else ""
        except Exception as e:
            print(f"[!] Failed to fetch detail for {url}: {e}")
            return ""

    def parse(self, raw_html):
        decoded_html = html.unescape(raw_html)
        soup = BeautifulSoup(decoded_html, "html.parser")
        jobs = []

        for card in soup.select("div.job_seen_beacon"):
            title_tag = card.select_one("h2.jobTitle a")
            company_tag = card.select_one("[data-testid='company-name']")
            location_tag = card.select_one("[data-testid='text-location']")
            salary_tag = card.select_one("[data-testid*='salary-snippet']")
            desc_tag = card.select_one("div[data-testid='belowJobSnippet']")
            posted_tag = card.select_one("span.date, span[aria-label*='ago']")

            title = title_tag.get_text(strip=True) if title_tag else ""
            company = company_tag.get_text(strip=True) if company_tag else ""
            location = location_tag.get_text(strip=True) if location_tag else ""
            salary = salary_tag.get_text(strip=True) if salary_tag else ""
            short_desc = desc_tag.get_text(" ", strip=True) if desc_tag else ""
            posted = posted_tag.get_text(strip=True) if posted_tag else ""

            href = title_tag.get("href") if title_tag else ""
            if href and href.startswith("/"):
                href = f"https://uk.indeed.com{href}"

            description = self.fetch_detail(href) if href else ""

            jobs.append({
                "company": company,
                "title": title,
                "location": location,
                "salary": salary,
                "description": description,
                "url": href,
                "posted": posted,
            })

            # polite delay between requests
            time.sleep(0.5)

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
        print(f"[✓] Inserted {len(jobs)} Indeed records")