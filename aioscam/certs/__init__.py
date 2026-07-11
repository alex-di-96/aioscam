"""
Bundled CA certificates for Max API TLS verification

Since the 2026 migration, platform-api2.max.ru serves a certificate issued by
the Russian Ministry of Digital Development (Минцифры) CA, which is absent
from the default trust store of most non-Russian operating systems.

This package bundles the official CA certificates (downloaded from
https://www.gosuslugi.ru/crt) so the framework can verify the Max API server
without touching the system-wide trust store — trust is scoped to the bot's
own HTTPS connections only.

    Root CA: Russian Trusted Root CA  (valid until 2032-02-27,
             SHA256 D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:
                    35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31)
    Sub CA:  Russian Trusted Sub CA   (valid until 2027-03-06)

Usage:
    from aioscam.certs import create_ssl_context
    context = create_ssl_context()  # system CAs + Russian Trusted CA
"""

import ssl
from pathlib import Path
from typing import List

_CERTS_DIR = Path(__file__).parent

RUSSIAN_TRUSTED_CA_FILES: List[Path] = [
    _CERTS_DIR / "russian_trusted_root_ca.crt",
    _CERTS_DIR / "russian_trusted_sub_ca.crt",
]


def create_ssl_context() -> ssl.SSLContext:
    """
    Create an SSL context trusting both the system CA store and the bundled
    Russian Trusted CA (Минцифры) certificates.

    Returns:
        ssl.SSLContext ready to be passed to aiohttp.TCPConnector(ssl=...)
    """
    context = ssl.create_default_context()
    for ca_file in RUSSIAN_TRUSTED_CA_FILES:
        context.load_verify_locations(cafile=str(ca_file))
    return context


__all__ = ["RUSSIAN_TRUSTED_CA_FILES", "create_ssl_context"]
