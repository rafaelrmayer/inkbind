"""Fetch article text while applying SSRF-oriented URL checks.

Important: application-level DNS checks alone cannot fully prevent DNS rebinding.
Deploy with network egress rules that block private, loopback, link-local,
reserved and metadata-service destinations as a second layer of defense.
"""
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

MAX_RESPONSE_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 15.0
ALLOWED_SCHEMES = {"http", "https"}


class UnsafeURLError(ValueError):
    """Raised when a URL is not safe to fetch."""


def validate_url(url: str) -> str:
    """Validate URL shape, port, hostname and all resolved IP addresses."""
    if not isinstance(url, str) or not url.strip() or len(url) > 2048:
        raise UnsafeURLError("URL inválida")
    try:
        parts = urlsplit(url.strip())
        scheme = parts.scheme.lower()
        hostname = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise UnsafeURLError("URL inválida") from exc

    if scheme not in ALLOWED_SCHEMES or not hostname:
        raise UnsafeURLError("A URL deve usar HTTP ou HTTPS e conter um host")
    if parts.username is not None or parts.password is not None:
        raise UnsafeURLError("Credenciais na URL não são permitidas")
    if port is not None and port != (443 if scheme == "https" else 80):
        raise UnsafeURLError("Porta não permitida")

    hostname = hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise UnsafeURLError("Host local não permitido")
    try:
        literal_ip = ipaddress.ip_address(hostname)
    except ValueError:
        literal_ip = None
    if literal_ip is not None:
        if not literal_ip.is_global:
            raise UnsafeURLError("Endereço IP não público não permitido")
    else:
        try:
            answers = socket.getaddrinfo(hostname, port or (443 if scheme == "https" else 80), type=socket.SOCK_STREAM)
        except OSError as exc:
            raise UnsafeURLError("Não foi possível resolver o host") from exc
        if not answers:
            raise UnsafeURLError("Host sem endereço IP válido")
        for answer in answers:
            address = answer[4][0].split("%", 1)[0]
            try:
                parsed_ip = ipaddress.ip_address(address)
            except ValueError as exc:
                raise UnsafeURLError("Endereço IP inválido para o host") from exc
            if not parsed_ip.is_global:
                raise UnsafeURLError("O host resolve para um endereço IP não público")

    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))


def scrape_post(url: str) -> dict:
    """Extract a page title and paragraphs without following unchecked redirects."""
    current_url = validate_url(url)
    headers = {"User-Agent": "Inkbind/0.1 (+article-to-pdf)", "Accept": "text/html,application/xhtml+xml"}

    with httpx.Client(follow_redirects=False, timeout=TIMEOUT_SECONDS, trust_env=False, headers=headers) as client:
        for redirect_count in range(MAX_REDIRECTS + 1):
            current_url = validate_url(current_url)
            with client.stream("GET", current_url) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    if redirect_count >= MAX_REDIRECTS:
                        raise ValueError("Limite de redirecionamentos excedido")
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirecionamento sem destino")
                    current_url = urljoin(current_url, location)
                    continue

                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    raise ValueError("A URL não retornou conteúdo HTML")
                chunks = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        raise ValueError("A página excede o limite de 5 MB")
                    chunks.append(chunk)
                html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
                final_url = str(response.url)
                break
        else:
            raise ValueError("Não foi possível concluir a requisição")

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if not title:
        heading = soup.find("h1")
        title = heading.get_text(" ", strip=True) if heading else "Sem título"
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p") if p.get_text(" ", strip=True)]
    if not paragraphs:
        raise ValueError("Nenhum parágrafo de texto foi encontrado na página")
    return {"title": title[:500], "paragraphs": paragraphs, "source_url": final_url}
