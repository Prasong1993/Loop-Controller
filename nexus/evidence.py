"""Conservative public HTTPS source fetch and exact-quote verification."""
from __future__ import annotations
from html.parser import HTMLParser
import http.client
import ipaddress
import socket
import ssl
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

def _validated_public_https_url(url:str):
    parsed=urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
        raise EvidenceFetchError("source URL must be an HTTPS URL without embedded credentials")
    if parsed.port not in (None,443):
        raise EvidenceFetchError("nonstandard HTTPS ports are not allowed")
    host=parsed.hostname.rstrip(".").lower()
    if host in {"localhost","localhost.localdomain"}:
        raise EvidenceFetchError("local hostnames are not allowed")
    try:
        addresses=[]
        for info in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM):
            address=ipaddress.ip_address(info[4][0])
            if address not in addresses:
                addresses.append(address)
    except (OSError,ValueError) as exc:
        raise EvidenceFetchError("source host could not be resolved") from exc
    if not addresses or any(not addr.is_global for addr in addresses):
        raise EvidenceFetchError("source host must resolve only to public IP addresses")
    return parsed, host, [str(address) for address in addresses]

def _validate_public_https_url(url:str)->str:
    _validated_public_https_url(url)
    return url

class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a previously validated IP while retaining TLS hostname checks."""
    def __init__(self, host, pinned_ip, **kwargs):
        self._pinned_ip=pinned_ip
        super().__init__(host, **kwargs)
    def connect(self):
        sock=socket.create_connection((self._pinned_ip,self.port),self.timeout,self.source_address)
        self.sock=self._context.wrap_socket(sock,server_hostname=self.host)

class _PinnedHTTPSHandler(HTTPSRedirectHandler):
    def __init__(self, pinned_ip, context=None):
        super().__init__()
        self.pinned_ip=pinned_ip
        self.context=context or ssl.create_default_context()
    def https_open(self, req):
        return self.do_open(lambda host, **kwargs: _PinnedHTTPSConnection(
            host,self.pinned_ip,**kwargs),req,context=self.context)

def fetch_public_text(url:str)->str:
    parsed, host, addresses = _validated_public_https_url(url)
    safe_url=url
    request=Request(safe_url,headers={"User-Agent":"NEXUS-EvidenceVerifier/0.1","Accept":"text/html,text/plain"})
    # Pin the connection to the address validated above to close the DNS
    # validation/connection time-of-check-to-time-of-use gap.
    opener=build_opener(_NoRedirect(),_PinnedHTTPSHandler(addresses[0]))
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
