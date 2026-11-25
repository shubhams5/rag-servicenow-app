from src.config import config
import os
import requests
import pytesseract
from PIL import Image
import io
import pdfplumber
import docx
import tempfile
import pandas as pd
from pptx import Presentation
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from src.utils.observability import log_info, log_error

SERVICENOW_URL = config.get("SERVICENOW_URL")
SERVICENOW_USER = config.get("SERVICENOW_USER")
SERVICENOW_PASS = config.get("SERVICENOW_PASS")
HTTP_TIMEOUT = float(config.get("HTTP_TIMEOUT_SECONDS", 30) or 30)

# Optional: set TESSERACT_CMD in env/config. Do not hardcode user profile paths.
_tesseract_cmd = config.get("TESSERACT_CMD") or os.environ.get("TESSERACT_CMD")
if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd


def fetch_attachments(article_sys_id):
    api_url = f"{SERVICENOW_URL}/api/now/table/sys_attachment"
    params = {"sysparm_query": f"table_sys_id={article_sys_id}^table_name=kb_knowledge"}
    try:
        response = requests.get(
            api_url,
            params=params,
            auth=(SERVICENOW_USER, SERVICENOW_PASS),
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        log_info(f"Fetched attachments for article {article_sys_id}")
        return response.json()["result"]
    except Exception as e:
        log_error(f"Failed to fetch attachments for article {article_sys_id}: {str(e)}")
        return []


def process_attachment(attachment):
    content_type = attachment.get("content_type", "")
    sys_id = attachment.get("sys_id", "")
    file_name = attachment.get("file_name", "unknown")
    download_url = f"{SERVICENOW_URL}/api/now/attachment/{sys_id}/file"

    try:
        response = requests.get(
            download_url,
            auth=(SERVICENOW_USER, SERVICENOW_PASS),
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
        content = response.content
    except Exception as e:
        log_error(f"Failed to download attachment {file_name} ({sys_id}): {str(e)}")
        return ""

    # Image
    if content_type in ["image/png", "image/jpeg"]:
        try:
            image = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            log_error(f"OCR failed for image {file_name}: {str(e)}")
            return ""

    # PDF
    elif content_type == "application/pdf":
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            with pdfplumber.open(temp_file_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if not page_text:
                        page_image = page.to_image(resolution=300)
                        page_text = pytesseract.image_to_string(page_image.original)
                    if page_text:
                        text += page_text + "\n"
            return text
        except Exception as e:
            log_error(f"PDF extraction failed for {file_name}: {str(e)}")
            return ""
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)

    # DOCX
    elif content_type.startswith("application/vnd.openxmlformats-officedoc"):
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            doc = docx.Document(temp_file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        except Exception as e:
            log_error(f"DOCX extraction failed for {file_name}: {str(e)}")
            return ""
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)

    # TXT
    elif content_type == "text/plain":
        try:
            text = content.decode("utf-8", errors="ignore")
            return text
        except Exception as e:
            log_error(f"TXT extraction failed for {file_name}: {str(e)}")
            return ""

    # CSV
    elif content_type == "text/csv" or file_name.lower().endswith(".csv"):
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            df = pd.read_csv(temp_file_path)
            text = df.to_string(index=False)
            return text
        except Exception as e:
            log_error(f"CSV extraction failed for {file_name}: {str(e)}")
            return ""
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)

    # XLSX
    elif (
        content_type
        == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        or file_name.lower().endswith(".xlsx")
    ):
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            df = pd.read_excel(temp_file_path)
            text = df.to_string(index=False)
            return text
        except Exception as e:
            log_error(f"XLSX extraction failed for {file_name}: {str(e)}")
            return ""
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)

    # PPTX
    elif (
        content_type
        == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        or file_name.lower().endswith(".pptx")
    ):
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            prs = Presentation(temp_file_path)
            text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        text += shape.text + "\n"
            return text
        except Exception as e:
            log_error(f"PPTX extraction failed for {file_name}: {str(e)}")
            return ""
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)

    # HTML
    elif content_type == "text/html" or file_name.lower().endswith(".html"):
        try:
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(separator="\n")
            return text
        except Exception as e:
            log_error(f"HTML extraction failed for {file_name}: {str(e)}")
            return ""

    # XML
    elif content_type == "application/xml" or file_name.lower().endswith(".xml"):
        try:
            root = ET.fromstring(content)
            text = ET.tostring(root, encoding="unicode", method="text")
            return text
        except Exception as e:
            log_error(f"XML extraction failed for {file_name}: {str(e)}")
            return ""

    # RTF, DOC (basic support, Windows only)
    elif content_type in [
        "application/rtf",
        "application/msword",
    ] or file_name.lower().endswith((".rtf", ".doc")):
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".doc") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            import win32com.client

            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            doc = word.Documents.Open(temp_file_path)
            text = doc.Content.Text
            doc.Close(False)
            word.Quit()
            return text
        except Exception as e:
            log_error(f"RTF/DOC extraction failed for {file_name}: {str(e)}")
            return ""
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.remove(temp_file.name)

    else:
        log_error(f"Unsupported attachment type for {file_name} ({content_type})")
        return ""
