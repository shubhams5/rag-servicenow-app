from src.storage.elasticsearch import ElasticsearchClient

es_client = ElasticsearchClient()
print(es_client.client.info())
