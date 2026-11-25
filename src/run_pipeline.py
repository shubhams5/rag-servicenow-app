import concurrent.futures
from datetime import datetime
from src.storage.elasticsearch import ElasticsearchClient
from src.servicenow.fetch_kb import fetch_kb_articles, fetch_kb_article_by_sys_id
from src.servicenow.fetch_attachments import fetch_attachments
from src.embeddings.chunk_and_embed import article_chunks
from src.utils.observability import log_info, log_error, log_exception

es_client = ElasticsearchClient()


def process_one_article(article):
    log_info(f"Processing article: {article.get('number', '')} ({article['sys_id']})")
    try:
        attachments = fetch_attachments(article["sys_id"])
        article_chunks(article, attachments)
        log_info(f"Article processed successfully: {article.get('number', '')}")
    except Exception as e:
        log_error(f"Failed to process article {article.get('number', '')}: {str(e)}")
        log_exception(e)
        failure_obj = {
            "failure_id": article["sys_id"],
            "article_number": article.get("number", ""),
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
        es_client.index_failure(failure_obj)


def reprocess_failures():
    failed_articles = es_client.fetch_failed_articles()
    log_info(f"Reprocessing {len(failed_articles)} failed articles")
    for failure in failed_articles:
        sys_id = failure["failure_id"]
        try:
            article = fetch_kb_article_by_sys_id(sys_id)
            attachments = fetch_attachments(sys_id)
            article_chunks(article, attachments)
            log_info(f"Reprocessed article successfully: {sys_id}")
            # Remove from failure index after success
            es_client.delete_failure_doc(sys_id)
        except Exception as e:
            log_error(f"Reprocessing failed for {sys_id}: {str(e)}")
            log_exception(e)


def main():
    articles = fetch_kb_articles(limit=20)
    log_info(f"Starting pipeline for {len(articles)} articles")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(process_one_article, articles)
    log_info("Pipeline run completed")
    reprocess_failures()


if __name__ == "__main__":
    main()
