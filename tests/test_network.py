import socket
import unittest
from unittest.mock import patch

from netroute_diagnose.dns import resolve_domain
from netroute_diagnose.egress import detect_egress


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self):
        return "https://example.invalid/ip"

    def read(self, _limit):
        return b'{"ip":"203.0.113.8"}'


class _FakeOpener:
    def open(self, _request, timeout):
        if timeout <= 0:
            raise AssertionError("timeout must be positive")
        return _FakeResponse()


class NetworkTests(unittest.TestCase):
    @patch("netroute_diagnose.dns.socket.getaddrinfo")
    def test_system_dns_collects_unique_addresses(self, getaddrinfo):
        getaddrinfo.return_value = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2001:db8::1", 0, 0, 0)),
        ]
        result = resolve_domain("example.com")
        self.assertEqual(result.addresses, ["192.0.2.1", "2001:db8::1"])
        self.assertIsNone(result.error)

    @patch("netroute_diagnose.egress.urllib.request.build_opener")
    def test_proxy_egress_extracts_json_ip(self, build_opener):
        build_opener.return_value = _FakeOpener()
        result = detect_egress(
            "clash",
            "https://example.invalid/ip",
            mode="proxy",
            proxy_url="http://127.0.0.1:7890",
        )
        self.assertEqual(result.ip, "203.0.113.8")
        self.assertIsNone(result.error)

    def test_proxy_mode_requires_proxy_url(self):
        result = detect_egress("clash", "https://example.invalid/ip", mode="proxy")
        self.assertIsNone(result.ip)
        self.assertIn("proxy_url", result.error or "")


if __name__ == "__main__":
    unittest.main()
