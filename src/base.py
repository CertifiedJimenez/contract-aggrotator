import os
import psycopg2
import redis
import requests
import json
from urllib.parse import urlparse
from datetime import datetime

class BaseClient:
    def __init__(self, pg_url=None, redis_url=None, broker_url=None):
        self.pg_url = pg_url or os.getenv(
            "POSTGRES_URL", "postgresql://postgres:postgres@localhost:5455/postgres"
        )
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        # broker URL for POSTing cmd/url/maxTimeout payloads
        self.broker_url = broker_url or os.getenv("BROKER_URL", "http://localhost:8191/v1")

        self.pg = self._connect_postgres()
        self.redis = self._connect_redis()
        self._ensure_table_exists()

        # initialize a persistent requests.Session for broker calls
        self._http = self._init_http_session()

    # -----------------------------------
    # HTTP session init
    # -----------------------------------
    def _init_http_session(self):
        s = requests.Session()
        s.headers.update({
            "User-Agent": "BaseClient/1.0 (+https://your.project/)",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        })
        return s

    # -----------------------------------
    # Private broker request helper
    # -----------------------------------
    def _request(
        self,
        cmd: str,
        url: str,
        maxTimeout: int = 60000,
        broker_url: str = None,
        params: dict = None,
        postData: dict | str = None,
    ):
        """
        Send a request to a FlareSolverr-like broker.

        Args:
            cmd: "request.get" or "request.post"
            url: target URL
            maxTimeout: timeout in ms (default 60000)
            broker_url: override broker endpoint (defaults to self.broker_url)
            params: optional extra JSON fields
            postData: optional body for POST; must be a URL-encoded string or dict

        Returns:
            Parsed JSON or raw text from broker.
        """
        service_url = broker_url or getattr(self, "broker_url", None)
        if not service_url:
            raise ValueError("No broker URL configured (broker_url / BROKER_URL)")

        payload = {
            "cmd": cmd,
            "url": url,
            "maxTimeout": int(maxTimeout),
        }

        # Merge any extra JSON params
        if params:
            payload.update(params)

        # For FlareSolverr, postData must be a string (not a dict)
        if postData:
            if isinstance(postData, dict):
                from urllib.parse import urlencode
                postData = urlencode(postData)
            payload["postData"] = postData

        timeout_seconds = (maxTimeout / 1000.0) + 10

        try:
            resp = self._http.post(service_url, json=payload, timeout=timeout_seconds)
            resp.raise_for_status()
            try:
                return resp.json()
            except ValueError:
                return resp.text
        except requests.RequestException as e:
            raise RuntimeError(f"Broker request failed: {e}") from e
        
    # -----------------------------------
    # (existing DB / Redis methods remain unchanged)
    # -----------------------------------
    def _connect_postgres(self):
        try:
            parsed = urlparse(self.pg_url)
            conn = psycopg2.connect(
                dbname=parsed.path.lstrip("/"),
                user=parsed.username,
                password=parsed.password,
                host=parsed.hostname,
                port=parsed.port,
            )
            conn.autocommit = True
            print(f"[✓] Connected to PostgreSQL → {self.pg_url}")
            return conn
        except Exception as e:
            print(f"[!] PostgreSQL connection failed: {e}")
            return None

    def _connect_redis(self):
        try:
            r = redis.from_url(self.redis_url, decode_responses=True)
            r.ping()
            print(f"[✓] Connected to Redis → {self.redis_url}")
            return r
        except Exception as e:
            print(f"[!] Redis connection failed: {e}")
            return None

    def _ensure_table_exists(self):
        if not self.pg:
            return
        with self.pg.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id SERIAL PRIMARY KEY,
                    company TEXT,
                    title TEXT,
                    description TEXT,
                    link TEXT UNIQUE,
                    date_posted TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            print("[✓] Ensured table 'jobs' exists")

    def insert_job(self, company, title, description, link, date_posted):
        if not self.pg:
            print("[!] PostgreSQL connection unavailable")
            return
        try:
            with self.pg.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO jobs (company, title, description, link, date_posted)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (link) DO UPDATE
                    SET company = EXCLUDED.company,
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        date_posted = EXCLUDED.date_posted;
                    """,
                    (company, title, description, link, date_posted),
                )
                print(f"[+] Job inserted → {title}")
        except Exception as e:
            print(f"[!] Insert failed for {title}: {e}")


class GenericScraper(BaseClient):
    BASE_URL = "..."  # define per site

    def fetch(self, url: str):
        """Use shared _request() to fetch HTML."""
        result = self._request(cmd="request.get", url=url, maxTimeout=60000)
        html_text = result.get("solution", {}).get("response", "") if isinstance(result, dict) else result
        return html_text

    def parse(self, html_text: str):
        """Extract jobs from the HTML (site-specific)."""
        raise NotImplementedError

    def run(self):
        html_text = self.fetch(self.BASE_URL)
        jobs = self.parse(html_text)
        for job in jobs:
            self.insert_job(
                company=job.get("company"),
                title=job.get("title"),
                description=job.get("description"),
                link=job.get("url"),
                date_posted=datetime.utcnow(),
            )