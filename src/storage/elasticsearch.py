from src.config import config
from elasticsearch import Elasticsearch, NotFoundError
from elasticsearch.helpers import bulk
from typing import List, Dict
from src.utils.observability import log_info, log_error
from elasticsearch.helpers import bulk, BulkIndexError


class ElasticsearchClient:
    def __init__(self):
        host = config.get("ELASTICSEARCH_HOST", "localhost")
        port = config.get("ELASTICSEARCH_PORT", "9200")
        user = config.get("ELASTICSEARCH_USER", "")
        password = config.get("ELASTICSEARCH_PASSWORD", "")
        use_ssl = config.get("ELASTICSEARCH_USE_SSL", "false").lower() == "true"
        protocol = "https" if use_ssl else "http"
        url = f"{protocol}://{host}:{port}"

        if user and password:
            self.client = Elasticsearch(url, basic_auth=(user, password))
        else:
            self.client = Elasticsearch(url)
        self.index_name = config.get("ELASTICSEARCH_INDEX_NAME", "articles")
        log_info(f"Elasticsearch client initialized for index: {self.index_name}")

    def index_article(self, article_id: str, article_data: Dict) -> None:
        try:
            self.client.index(index=self.index_name, id=article_id, body=article_data)
        except Exception as e:
            log_error(f"Failed to index article {article_id}: {str(e)}")

    def query_articles(self, query: str) -> List[Dict]:
        try:
            response = self.client.search(
                index=self.index_name, body={"query": {"match": {"content": query}}}
            )
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            log_error(f"Failed to query articles: {str(e)}")
            return []

    def article_exists(self, article_id: str) -> bool:
        try:
            self.client.get(index=self.index_name, id=article_id)
            return True
        except NotFoundError:
            return False
        except Exception as e:
            log_error(f"Error checking existence for article {article_id}: {str(e)}")
            return False

    def update_article(self, article_id: str, article_data: Dict) -> None:
        if self.article_exists(article_id):
            try:
                self.client.update(
                    index=self.index_name, id=article_id, body={"doc": article_data}
                )
            except Exception as e:
                log_error(f"Failed to update article {article_id}: {str(e)}")
        else:
            self.index_article(article_id, article_data)

    def bulk_index_articles(self, chunk_objs: List[Dict]) -> None:
        from src.rag.kb_fields import make_document_id

        actions = []
        for chunk_obj in chunk_objs:
            doc_id = chunk_obj.get("doc_id") or make_document_id(
                str(chunk_obj.get("sys_id", "")),
                str(chunk_obj.get("chunk_no", "")),
            )
            actions.append(
                {
                    "_index": self.index_name,
                    "_id": doc_id,
                    "_source": chunk_obj,
                }
            )
        try:
            bulk(self.client, actions, request_timeout=60)
        except BulkIndexError as e:
            log_error(f"Bulk indexing failed: {e.errors}")
        except Exception as e:
            log_error(f"Bulk indexing failed: {str(e)}")

    def index_failure(self, failure_obj: dict):
        failure_index = config.get("ELASTICSEARCH_FAILURE_INDEX", "article_failures")
        try:
            self.client.index(
                index=failure_index, id=failure_obj["failure_id"], document=failure_obj
            )
        except Exception as e:
            log_error(
                f"Failed to index failure record {failure_obj['failure_id']}: {str(e)}"
            )

    def fetch_failed_articles(self):
        failure_index = config.get("ELASTICSEARCH_FAILURE_INDEX", "article_failures")
        query = {"query": {"match_all": {}}}
        try:
            resp = self.client.search(index=failure_index, body=query, size=100)
            return [hit["_source"] for hit in resp["hits"]["hits"]]
        except Exception as e:
            log_error(f"Failed to fetch failed articles: {str(e)}")
            return []

    def delete_failure_doc(self, failure_id):
        failure_index = config.get("ELASTICSEARCH_FAILURE_INDEX", "article_failures")
        self.client.delete(index=failure_index, id=failure_id, ignore=[404])

    def semantic_query_articles(
        self, query: str, field: str = "chunk_semantic", size: int = 5
    ) -> List[Dict]:
        """
        Perform semantic search using ELSER on the specified semantic_text field.
        Raises on backend failure so callers can map to HTTP 503.
        """
        try:
            body = {
                "size": size,
                "query": {"semantic": {"field": field, "query": query}},
            }
            response = self.client.search(index=self.index_name, body=body)
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            log_error(f"Failed to perform semantic query: {str(e)}")
            raise

    def custom_query_articles(self, query_body: dict) -> List[Dict]:
        """
        Perform a custom search using the provided query body.
        Raises on backend failure so callers can map to HTTP 503.
        """
        try:
            response = self.client.search(index=self.index_name, body=query_body)
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            log_error(f"Failed to perform custom query: {str(e)}")
            raise
