"""Conservative public HTTPS source fetch and exact-quote verification."""
from __future__ import annotations
from html.parser import HTMLParser
import ipaddress
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

MAX_BYTES = 1_000_000
TIMEOUT_SECONDS = 8

class EvidenceFetchError(ValueError):
    pass

class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise EvidenceFetchError("redirects are not followed; verify the final HTTPS URL explicitly")

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts=[]
        self.hidden=0
    def handle_starttag(self, tag, attrs):
        if tag in {"script","style","noscript","svg"}: self.hidden+=1
    def handle_endtag(self, tag):
        if tag in {"script","style","noscript","svg"} and self.hidden: self.hidden-=1
        if tag in {"p","div","li","br","h1","h2","h3","tr"}: self.parts.append(" ")
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def _validate_public_https_url(url:str)->str:
    parsed=urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
        raise EvidenceFetchError("source URL must be an HTTPS URL without embedded credentials")
    if parsed.port not in (None,443):
        raise EvidenceFetchError("nonstandard HTTPS ports are not allowed")
    host=parsed.hostname.rstrip(".").lower()
    if host in {"localhost","localhost.localdomain"}:
        raise EvidenceFetchError("local hostnames are not allowed")
    try:
        addresses={ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host,None)}
    except (OSError,ValueError) as exc:
        raise EvidenceFetchError("source host could not be resolved") from exc
    if not addresses or any(not addr.is_global for addr in addresses):
        raise EvidenceFetchError("source host must resolve only to public IP addresses")
    return url

def fetch_public_text(url:str)->str:
    safe_url=_validate_public_https_url(url)
    request=Request(safe_url,headers={"User-Agent":"NEXUS-EvidenceVerifier/0.1","Accept":"text/html,text/plain"})
    opener=build_opener(_NoRedirect())
    try:
        with opener.open(request,timeout=TIMEOUT_SECONDS) as response:
            content_type=response.headers.get_content_type()
            if content_type not in {"text/html","text/plain","application/xhtml+xml"}:
                raise EvidenceFetchError("unsupported source content type")
            raw=response.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:
                raise EvidenceFetchError("source exceeds the 1 MB verification limit")
            charset=response.headers.get_content_charset() or "utf-8"
            decoded=raw.decode(charset,errors="replace")
    except EvidenceFetchError:
        raise
    except (HTTPError,URLError,TimeoutError,OSError,UnicodeError) as exc:
        raise EvidenceFetchError(f"source fetch failed: {type(exc).__name__}") from exc
    if content_type in {"text/html","application/xhtml+xml"}:
        parser=_TextExtractor()
        parser.feed(decoded)
        decoded=" ".join(" ".join(parser.parts).split())
    return decoded

def verify_source_quote(url:str,quoted_text:str,fetcher=fetch_public_text)->dict:
    if not quoted_text or not quoted_text.strip():
        raise EvidenceFetchError("quoted_text is required")
    text=fetcher(url)
    normalized=lambda value:" ".join(value.casefold().split())
    if normalized(quoted_text) not in normalized(text):
        raise EvidenceFetchError("quoted text was not found in fetched source")
    return {"source_text":text,"quoted_text":quoted_text.strip(),"source_chars":len(text),
            "method":"exact normalized quote match","source_url":url}
