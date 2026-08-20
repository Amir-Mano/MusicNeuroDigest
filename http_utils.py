"""Shared HTTP GET helper with a couple of quick retries on transient
failures (connection errors, timeouts, 5xx, or a raise_for_status
HTTPError) before giving up. On success or exhausted retries, behaves the
same as calling requests.get() + raise_for_status() directly -- just
retried first, since most of what killed runs so far (a flaky upstream API)
is exactly the kind of blip a retry recovers from without any run ever
seeing a failure at all.
"""

import logging
import time

import requests

log = logging.getLogger(__name__)

_RETRY_DELAYS = (2, 5)  # seconds to wait before each retry; 1 + len(...) attempts total


def get_with_retry(url: str, *, params: dict | None = None, timeout: int = 30) -> requests.Response:
    attempts = len(_RETRY_DELAYS) + 1
    last_exc: requests.RequestException | None = None

    for attempt in range(attempts):
        if attempt > 0:
            time.sleep(_RETRY_DELAYS[attempt - 1])
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            log.warning("GET %s failed (attempt %d/%d): %s", url, attempt + 1, attempts, exc)

    raise last_exc
