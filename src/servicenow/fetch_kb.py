import requests

from src.config import config
from src.utils.observability import log_error, log_info

SERVICENOW_URL = config.get("SERVICENOW_URL")
SERVICENOW_USER = config.get("SERVICENOW_USER")
SERVICENOW_PASS = config.get("SERVICENOW_PASS")
HTTP_TIMEOUT = float(config.get("HTTP_TIMEOUT_SECONDS", 30) or 30)


def fetch_kb_articles(limit=20):
    api_url = f"{SERVICENOW_URL}/api/now/table/kb_knowledge"
    params = {
        "sysparm_query": "active=true^workflow_state=published^textISNOTEMPTY",
        "sysparm_display_value": "true",
        "sysparm_fields": "sys_id,article_id,number,short_description,meta_description,text,topic,category,author,published,active",
        "sysparm_limit": str(limit),
    }
    try:
        response = requests.get(
            api_url,
            params=params,
            auth=(SERVICENOW_USER, SERVICENOW_PASS),
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        log_info(f"Fetched {limit} KB articles")
        return response.json()["result"]
    except Exception as e:
        log_error(f"Failed to fetch KB articles: {str(e)}")
        return []


def fetch_kb_article_by_sys_id(sys_id):
    api_url = f"{SERVICENOW_URL}/api/now/table/kb_knowledge/{sys_id}"
    params = {
        "sysparm_display_value": "true",
        "sysparm_fields": "sys_id,article_id,number,short_description,meta_description,text,topic,category,author,published,active",
    }
    try:
        response = requests.get(
            api_url,
            params=params,
            auth=(SERVICENOW_USER, SERVICENOW_PASS),
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        log_info(f"Fetched KB article {sys_id}")
        return response.json()["result"]
    except Exception as e:
        log_error(f"Failed to fetch KB article {sys_id}: {str(e)}")
        return None
