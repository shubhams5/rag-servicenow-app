import requests
import json
import os
from typing import List
from dotenv import load_dotenv
from storage.elasticsearch import ElasticsearchClient
from types.article import Article

load_dotenv()


class ServiceNowClient:
    def __init__(self):
        self.base_url = os.getenv("SERVICENOW_BASE_URL")
        self.username = os.getenv("SERVICENOW_USERNAME")
        self.password = os.getenv("SERVICENOW_PASSWORD")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_kb_articles(self, sysparm_limit: int = 100) -> List[Article]:
        url = (
            f"{self.base_url}/api/now/table/kb_knowledge?sysparm_limit={sysparm_limit}"
        )
        response = requests.get(
            url, auth=(self.username, self.password), headers=self.headers
        )

        if response.status_code != 200:
            raise Exception(
                f"Failed to fetch articles: {response.status_code} {response.text}"
            )

        articles_data = response.json().get("result", [])
        return [Article(**article) for article in articles_data]


def ingest_articles():
    client = ServiceNowClient()
    elasticsearch_client = ElasticsearchClient()

    try:
        articles = client.get_kb_articles()
        for article in articles:
            elasticsearch_client.index_article(article)
    except Exception as e:
        print(f"Error during ingestion: {e}")


if __name__ == "__main__":
    ingest_articles()
