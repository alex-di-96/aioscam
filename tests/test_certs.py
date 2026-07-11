"""
Tests for bundled Russian Trusted CA certificates (aioscam.certs)
"""

import ssl

import pytest

from aioscam.certs import RUSSIAN_TRUSTED_CA_FILES, create_ssl_context


class TestBundledCerts:
    def test_cert_files_exist(self):
        for ca_file in RUSSIAN_TRUSTED_CA_FILES:
            assert ca_file.is_file(), f"missing bundled cert: {ca_file}"

    def test_cert_files_are_pem(self):
        for ca_file in RUSSIAN_TRUSTED_CA_FILES:
            content = ca_file.read_text()
            assert content.startswith("-----BEGIN CERTIFICATE-----")
            assert content.rstrip().endswith("-----END CERTIFICATE-----")

    def test_create_ssl_context(self):
        context = create_ssl_context()
        assert isinstance(context, ssl.SSLContext)
        # Default verification stays intact
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True

    def test_context_contains_russian_ca(self):
        context = create_ssl_context()
        subjects = [
            rdn
            for cert in context.get_ca_certs()
            for field in cert.get("subject", ())
            for rdn in field
        ]
        assert ("organizationName", "The Ministry of Digital Development and Communications") in subjects


class TestClientSslWiring:
    def test_client_uses_bundled_context_by_default(self):
        from aioscam.client import AioScamClient

        client = AioScamClient(token="t")
        assert isinstance(client._ssl_context, ssl.SSLContext)

    def test_client_accepts_custom_context(self):
        from aioscam.client import AioScamClient

        custom = ssl.create_default_context()
        client = AioScamClient(token="t", ssl_context=custom)
        assert client._ssl_context is custom

    def test_bot_passes_ssl_context(self):
        from aioscam import Bot

        custom = ssl.create_default_context()
        bot = Bot(token="t", ssl_context=custom)
        assert bot._client._ssl_context is custom

    @pytest.mark.asyncio
    async def test_session_created_with_connector(self):
        from aioscam.client import AioScamClient

        client = AioScamClient(token="t")
        session = await client._get_session()
        try:
            assert session.connector is not None
        finally:
            await client.close()
