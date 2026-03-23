"""
Shared HTTP utilities with retry logic.

Provides a configured requests Session with automatic retry
on transient failures (429, 500, 502, 503, 504).
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def create_retry_session(
    retries: int = 3,
    backoff_factor: float = 1.0,
    status_forcelist: tuple = (429, 500, 502, 503, 504),
    timeout: int = 30,
) -> requests.Session:
    """
    Create a requests Session with automatic retry on transient failures.

    Args:
        retries: Number of retries (default: 3)
        backoff_factor: Exponential backoff factor (default: 1.0 -> 1s, 2s, 4s)
        status_forcelist: HTTP status codes to retry on
        timeout: Default request timeout in seconds

    Returns:
        Configured requests.Session
    """
    session = requests.Session()

    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Store default timeout on the session for convenience
    session._default_timeout = timeout

    return session


def get_with_retry(url: str, session: requests.Session = None, **kwargs) -> requests.Response:
    """
    Perform a GET request with retry logic.

    Args:
        url: URL to fetch
        session: Optional pre-configured session (creates one if not provided)
        **kwargs: Additional arguments passed to session.get()

    Returns:
        requests.Response

    Raises:
        requests.RequestException: If all retries fail
    """
    if session is None:
        session = create_retry_session()

    kwargs.setdefault('timeout', getattr(session, '_default_timeout', 30))
    response = session.get(url, **kwargs)
    response.raise_for_status()
    return response
