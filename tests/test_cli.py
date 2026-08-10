from __future__ import annotations

import unittest
from unittest.mock import patch

from verlane.cli import _parse_context_size, edit_context_size
from verlane.settings import Settings


class ContextSizeTests(unittest.TestCase):
    def test_parse_context_size_supports_plain_k_and_m_values(self) -> None:
        cases = {
            "32768": 32768,
            "32k": 32768,
            "32K": 32768,
            "128k": 131072,
            "1m": 1048576,
            "1M": 1048576,
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(_parse_context_size(value), expected)

    def test_parse_context_size_rejects_invalid_values(self) -> None:
        for value in ("", "0", "-1", "k", "m", "1.5k", "32kb", "abc"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _parse_context_size(value)

    def test_edit_context_size_accepts_k_suffix(self) -> None:
        settings = Settings()
        with patch("verlane.cli.typer.prompt", return_value="32k"):
            edit_context_size(settings)
        self.assertEqual(settings.context_size, 32768)

    def test_edit_context_size_empty_value_restores_default(self) -> None:
        settings = Settings(context_size=32768)
        with patch("verlane.cli.typer.prompt", return_value=""):
            edit_context_size(settings)
        self.assertIsNone(settings.context_size)


if __name__ == "__main__":
    unittest.main()
