from .base import BaseClient
from bs4 import BeautifulSoup
import html
from datetime import datetime

class JobServeScraper(BaseClient):
    BASE_URL = "https://jobserve.com/WebServices/JobSearch.asmx/RetrieveJobs"
    DETAIL_URL = "https://jobserve.com/WebServices/JobSearch.asmx/RetrieveSingleJobDetail"
    SHID = "FA2A016D3A8D7AED9536"

    def __init__(self):
        super().__init__()
        self.job_ids = (
            "CC63F910C3F64BEDD4#"
            "98B8FACED3D7C8415A#"
            "84BB13E2FBA268EABB#"
            "0F920EE53C27414151#"
            "1ACB54BB4164C389EB"
        )

    def fetch(self, page=1):
        payload = {"shid": self.SHID, "jobIDsStr": self.job_ids, "pageNum": str(page)}
        result = self._request("request.post", self.BASE_URL, maxTimeout=60000, postData=payload)
        return result.get("solution", {}).get("response", "") if isinstance(result, dict) else result

    def parse(self, raw_html):
        decoded_html = html.unescape(raw_html)
        soup = BeautifulSoup(decoded_html, "html.parser")
        jobs = []
        for item in soup.select(".jobItem"):
            title = item.select_one(".jobResultsTitle")
            company = item.select_one(".jobResultsCompany")
            desc = item.select_one(".jobResultsDesc")
            posted = item.select_one(".when")
            url = item.select_one(".jobResultsTitle a")
            jobs.append({
                "company": company.get_text(strip=True) if company else "",
                "title": title.get_text(strip=True) if title else "",
                "description": desc.get_text(strip=True) if desc else "",
                "url": url["href"] if url and url.has_attr("href") else "",
                "posted": posted.get_text(strip=True) if posted else ""
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
        print(f"[✓] Inserted {len(jobs)} JobServe records")