from .base import BaseClient
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlencode
import html
import time


class LinkedInScraper(BaseClient):
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def __init__(self, keyword="Django", location="London", pages=1, sortby="DD"):
        """
        sortby:
          - 'DD' = Date Descending (Newest)
          - 'DA' = Date Ascending (Oldest)
          - 'R'  = Relevance
        """
        super().__init__()
        self.keyword = keyword
        self.location = location
        self.pages = pages
        self.sortby = sortby

    def fetch_page(self, index=0):
        """Fetch a batch of job listings from LinkedIn's guest jobs API."""
        query = {
            "keywords": self.keyword,
            "location": self.location,
            "start": index,
            "sortBy": self.sortby,
        }

        url = f"{self.BASE_URL}?{urlencode(query)}"
        result = self._request("request.get", url, maxTimeout=60000)
        html_text = result.get("solution", {}).get("response", "") if isinstance(result, dict) else result
        return html_text or ""

    def fetch_detail(self, url):
        """Fetch full job description from the LinkedIn job page."""
        try:
            result = self._request("request.get", url, maxTimeout=60000)
            html_text = result.get("solution", {}).get("response", "") if isinstance(result, dict) else result
            soup = BeautifulSoup(html.unescape(html_text), "html.parser")
            desc_el = soup.select_one(".show-more-less-html__markup")
            return desc_el.get_text(" ", strip=True) if desc_el else ""
        except Exception as e:
            print(f"[!] Failed to fetch detail for {url}: {e}")
            return ""

    def parse(self, raw_html):
        soup = BeautifulSoup(raw_html, "html.parser")
        jobs = []

        for card in soup.select("li"):
            title_el = card.select_one("h3.base-search-card__title")
            company_el = card.select_one("h4.base-search-card__subtitle a")
            location_el = card.select_one("span.job-search-card__location")
            posted_el = card.select_one("time")
            link_el = card.select_one("a.base-card__full-link")

            title = title_el.get_text(strip=True) if title_el else ""
            company = company_el.get_text(strip=True) if company_el else ""
            location = location_el.get_text(strip=True) if location_el else ""
            posted = posted_el.get("datetime", "") if posted_el else ""
            link = link_el.get("href") if link_el else ""

            # optional full description fetch
            full_desc = self.fetch_detail(link) if link else ""

            jobs.append({
                "company": company,
                "title": title,
                "location": location,
                "description": full_desc,
                "url": link,
                "posted": posted,
            })

            time.sleep(0.5)

        return jobs

    def run(self):
        total_jobs = 0
        for page in range(self.pages):
            index = page * 25  # LinkedIn loads 25 per batch
            html_text = self.fetch_page(index)
            jobs = self.parse(html_text)
            total_jobs += len(jobs)

            for job in jobs:
                self.insert_job(
                    company=job["company"],
                    title=job["title"],
                    description=job["description"],
                    link=job["url"],
                    date_posted=datetime.utcnow(),
                )

        print(f"[✓] Inserted {total_jobs} LinkedIn records")