"""Generate PDFs from extracted text without interpreting it as HTML."""
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

from weasyprint import HTML


def _safe_source_label(source_url: str) -> str:
    """Return a display-safe URL string; the URL is never fetched by WeasyPrint."""
    parts = urlsplit(str(source_url))
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return "Fonte não informada"
    return escape(f"{parts.scheme}://{parts.netloc}{parts.path}", quote=True)


def _deny_external_resource(url: str, *args, **kwargs):
    raise ValueError("Carregamento de recursos externos desativado no PDF")


def build_pdf(post_data: dict, output_path: str) -> str:
    title = escape(str(post_data.get("title", "Sem título")), quote=True)
    paragraphs = post_data.get("paragraphs", [])
    if not isinstance(paragraphs, list):
        raise ValueError("O conteúdo do artigo é inválido")
    body_html = "".join(f"<p>{escape(str(p), quote=True)}</p>" for p in paragraphs)
    source_label = _safe_source_label(post_data.get("source_url", ""))
    html = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><style>
    @page {{ size: A4; margin: 2cm; }}
    body {{ font-family: Georgia, serif; line-height: 1.6; color: #222; overflow-wrap: break-word; }}
    h1 {{ font-size: 24pt; border-bottom: 2px solid #333; padding-bottom: 10px; }}
    p {{ text-align: justify; margin-bottom: 1em; }}
    .meta {{ color: #888; font-size: 10pt; margin-top: 2em; overflow-wrap: break-word; }}
    </style></head><body><h1>{title}</h1>{body_html}
    <p class="meta">Gerado por Inkbind a partir de {source_label}</p></body></html>"""
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html, url_fetcher=_deny_external_resource).write_pdf(str(destination))
    return str(destination)
