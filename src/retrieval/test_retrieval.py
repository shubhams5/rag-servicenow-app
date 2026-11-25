from src.rag.ticket_retrieval import get_related_kbs

# Example ticket dict
ticket = {
    "number": "INC0012345",
    "short_description": "VPN not connecting",
    "description": "User unable to connect to VPN from home network.",
    "category": "Network",
    "subcategory": "VPN",
    "cmdb_ci": "LAPTOP-1234",
}

# Get related KBs
related_articles = get_related_kbs(ticket, top_k=5)
print(related_articles)
