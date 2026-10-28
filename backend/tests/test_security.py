import html

import pytest

from app.builder import _safe_source_label
from app.scraper import UnsafeURLError, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/article",
        "http://localhost/admin",
        "http://127.0.0.1/",
        "http://10.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://user:pass@example.com/",
        "http://example.com:8080/",
    ],
)
def test_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeURLError):
        validate_url(url)


def test_accepts_public_ip_and_normalizes_fragment():
    assert validate_url("https://8.8.8.8/article#section") == "https://8.8.8.8/article"


def test_source_label_rejects_non_http_scheme():
    assert _safe_source_label("file:///etc/passwd") == "Fonte não informada"


def test_html_escape_is_available_for_untrusted_content():
    payload = '<script>alert("x")</script>'
    assert html.escape(payload, quote=True) == "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"
