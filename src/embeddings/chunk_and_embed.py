import requests
from bs4 import BeautifulSoup

from src.config import config
from src.rag.kb_fields import ELSER_INFERENCE_ID, make_document_id, safe_chunk_step
from src.servicenow.fetch_attachments import process_attachment
from src.storage.elasticsearch import ElasticsearchClient
from src.utils.observability import log_error, log_info

CHUNK_SIZE = int(config.get("CHUNK_SIZE", 512) or 512)
CHUNK_OVERLAP = int(config.get("CHUNK_OVERLAP", 50) or 50)

es_client = ElasticsearchClient()


def sanitize_title(title):
    return "".join(c if c.isalnum() else "_" for c in title)


def sanitize_filename(filename):
    return "".join(c if c.isalnum() else "_" for c in filename)


def clean_html(text):
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ")


def chunk_text(text, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    words = text.split()
    chunks = []
    i = 0
    step = safe_chunk_step(chunk_size, chunk_overlap)
    size = int(chunk_size) if int(chunk_size) > 0 else 512
    while i < len(words):
        chunks.append(" ".join(words[i : i + size]))
        i += step
    return chunks


def _elser_infer_url() -> str:
    host = config.get("ELASTICSEARCH_HOST", "localhost")
    port = config.get("ELASTICSEARCH_PORT", "9200")
    use_ssl = str(config.get("ELASTICSEARCH_USE_SSL", "false")).lower() == "true"
    protocol = "https" if use_ssl else "http"
    return (
        f"{protocol}://{host}:{port}/_ml/trained_models/"
        f"{ELSER_INFERENCE_ID}/_infer"
    )


def run_elser_inference(text):
    es_url = _elser_infer_url()
    payload = {"docs": [{"text_field": text}]}
    user = config.get("ELASTICSEARCH_USER") or ""
    password = config.get("ELASTICSEARCH_PASSWORD") or ""
    auth = (user, password) if user and password else None
    response = requests.post(es_url, json=payload, timeout=30, auth=auth)
    if response.ok:
        results = response.json()["inference_results"][0]
        return results.get("sparse_vector", {})
    else:
        log_error(f"ELSER inference failed: {response.text}")
        return {}


def extract_tags(text, top_n=5):
    # Simple keyword extraction: returns top N unique words longer than 4 chars
    words = [w.lower() for w in clean_html(text).split() if len(w) > 4]
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq, key=freq.get, reverse=True)
    return sorted_words[:top_n]


def article_chunks(article, attachments):
    pages = [
        {
            "page_no": 1,
            "title": article.get("short_description", "Untitled"),
            "sections": [{"section_no": 1, "text": article["text"]}],
        }
    ]
    all_chunks = []

    # Article chunks
    for page in pages:
        page_no = page["page_no"]
        title = page["title"]
        sanitized_title = sanitize_title(title)
        for section in page["sections"]:
            section_no = section["section_no"]
            section_text = section["text"]
            chunks = chunk_text(section_text)
            for chunk_seq_number, chunk in enumerate(chunks):
                chunk_no = (
                    f"{page_no}_{sanitized_title}_{section_no}_{chunk_seq_number}"
                )
                prev_chunk_no = (
                    f"{page_no}_{sanitized_title}_{section_no}_{chunk_seq_number-1}"
                    if chunk_seq_number > 0
                    else ""
                )
                next_chunk_no = (
                    f"{page_no}_{sanitized_title}_{section_no}_{chunk_seq_number+1}"
                    if chunk_seq_number < len(chunks) - 1
                    else ""
                )
                cleaned_chunk = clean_html(chunk)
                doc_id = make_document_id(article["sys_id"], chunk_no)
                chunk_obj = {
                    "type": "article",
                    "sys_id": article["sys_id"],
                    "article_number": article.get("number", ""),
                    "page_no": page_no,
                    "title": title,
                    "section_no": section_no,
                    "chunk_no": chunk_no,
                    "doc_id": doc_id,
                    "chunk": chunk,
                    "chunk_semantic": cleaned_chunk,  # For ELSER semantic_text field
                    "prev_chunk_no": prev_chunk_no,
                    "next_chunk_no": next_chunk_no,
                    "tags": extract_tags(chunk),
                    # Add ELSER sparse vectors:
                    "elser_chunk_content": run_elser_inference(cleaned_chunk),
                    "elser_title": run_elser_inference(title),
                    "elser_keywords": run_elser_inference(
                        " ".join(extract_tags(chunk))
                    ),
                }
                all_chunks.append(chunk_obj)

    # Attachment chunks
    for attachment in attachments:
        att_text = process_attachment(attachment)
        if (
            not att_text.strip()
            or att_text.strip().lower() == "extracted text from attachment"
        ):
            continue
        att_chunks = chunk_text(att_text)
        sanitized_filename = sanitize_filename(
            attachment.get("file_name", "attachment")
        )
        for chunk_seq_number, chunk in enumerate(att_chunks):
            chunk_no = f"1_{sanitized_filename}_1_{chunk_seq_number}"
            prev_chunk_no = (
                f"1_{sanitized_filename}_1_{chunk_seq_number-1}"
                if chunk_seq_number > 0
                else ""
            )
            next_chunk_no = (
                f"1_{sanitized_filename}_1_{chunk_seq_number+1}"
                if chunk_seq_number < len(att_chunks) - 1
                else ""
            )
            cleaned_chunk = clean_html(chunk)
            # Include parent article sys_id so attachment chunks stay unique per article.
            parent_sys_id = article.get("sys_id", "")
            att_sys_id = attachment.get("sys_id", "")
            doc_id = make_document_id(
                f"{parent_sys_id}_{att_sys_id}", chunk_no
            )
            chunk_obj = {
                "type": "attachment",
                "sys_id": att_sys_id,
                "article_sys_id": parent_sys_id,
                "article_number": article.get("number", ""),
                "page_no": 1,
                "title": attachment.get("file_name", "attachment"),
                "section_no": 1,
                "chunk_no": chunk_no,
                "doc_id": doc_id,
                "chunk": chunk,
                "chunk_semantic": cleaned_chunk,  # For ELSER semantic_text field
                "prev_chunk_no": prev_chunk_no,
                "next_chunk_no": next_chunk_no,
                "tags": extract_tags(chunk),
                # Add ELSER sparse vectors:
                "elser_chunk_content": run_elser_inference(cleaned_chunk),
                "elser_title": run_elser_inference(
                    attachment.get("file_name", "attachment")
                ),
                "elser_keywords": run_elser_inference(" ".join(extract_tags(chunk))),
            }
            all_chunks.append(chunk_obj)

    # Bulk index all chunks at once
    if all_chunks:
        try:
            es_client.bulk_index_articles(all_chunks)
            log_info(
                f"Indexed {len(all_chunks)} chunks for article {article['number']}"
            )
        except Exception as e:
            log_error(f"Bulk indexing failed for article {article['number']}: {str(e)}")
