"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
import requests_mock as rm

from briefklick import BriefKlickClient


@pytest.fixture
def base_url() -> str:
    return "https://api.test.local/v2"


@pytest.fixture
def client(base_url: str) -> BriefKlickClient:
    return BriefKlickClient("test-key", base_url=base_url)


@pytest.fixture
def mock_http():
    with rm.Mocker() as m:
        yield m
