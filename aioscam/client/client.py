"""
HTTP Client for Max API
"""

import logging
from typing import Any, Dict, Optional

import aiohttp

from aioscam.client.request import RequestBuilder
from aioscam.client.response import Response
from aioscam.enums import ApiPath, HttpMethod
from aioscam.exceptions import ApiError, NetworkError, TimeoutError, UnauthorizedError, ForbiddenError, NotFoundError, RetryAfter
from aioscam.limiter import RateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)


class AioScamClient:
    """
    Async HTTP client for Max API

    Usage:
        async with AioScamClient(token="...") as client:
            response = await client.request("/getMe", HttpMethod.GET)
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://max.ru/api/bot",
        timeout: int = 30,
        session: Optional[aiohttp.ClientSession] = None,
        rate_limit: Optional[RateLimitConfig] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        self.token = token
        self.base_url = base_url
        self.default_timeout = timeout
        self._session = session
        self._close_session = False

        # Rate limiter: use provided instance or create from config
        if rate_limiter is not None:
            self.rate_limiter = rate_limiter
        else:
            self.rate_limiter = RateLimiter(rate_limit or RateLimitConfig())

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._close_session = True
        return self._session

    async def request(
        self,
        path: str,
        method: HttpMethod = HttpMethod.POST,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        token: Optional[str] = None,
    ) -> Response:
        """
        Make HTTP request to Max API (through rate limiter)

        Args:
            path: API endpoint path
            method: HTTP method
            body: Request body (for POST)
            params: Query parameters (for GET)
            timeout: Request timeout in seconds
            token: Bot token (overrides instance token)

        Returns:
            Response object
        """
        return await self.rate_limiter.execute(
            self._do_request, path, method, body, params, timeout, token
        )

    async def _do_request(
        self,
        path: str,
        method: HttpMethod = HttpMethod.POST,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        token: Optional[str] = None,
    ) -> Response:
        """Internal request implementation (called through rate limiter)"""
        session = await self._get_session()
        # Support both relative paths and absolute URLs
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self.base_url}{path}"

        request_builder = RequestBuilder(path, method)
        request_builder.set_token(token or self.token or "")

        if body:
            logger.info(f"Request body: {body}")
            request_builder.set_body(body)

        if params:
            request_builder.set_params(params)

        if timeout:
            request_builder.set_timeout(timeout)
        else:
            request_builder.set_timeout(self.default_timeout)

        request_data = request_builder.build()

        try:
            logger.debug(f"Request: {method.value} {url}")
            logger.info(f"Making request to: {url}")

            async with session.request(
                method=method.value,
                url=url,
                params=request_data.get("params"),
                headers=request_data.get("headers"),
                **({"json": request_data["json"]} if "json" in request_data else {}),
                timeout=aiohttp.ClientTimeout(total=request_data["timeout"]),
            ) as resp:
                logger.info(f"Response status: {resp.status}")
                response_text = await resp.text()
                logger.debug(f"Response body: {response_text[:500]}")

                try:
                    response_data = await resp.json()
                except:
                    response_data = {"raw": response_text}

                response = Response(
                    ok=resp.status == 200,
                    result=response_data,
                    status_code=resp.status,
                    headers=dict(resp.headers),
                    error=None if resp.status == 200 else f"HTTP {resp.status}",
                )

                if not response.ok:
                    logger.error(f"Error response body: {response_text[:500]}")
                    self._handle_error(response)

                logger.debug(f"Response: {resp.status}")
                return response

        except aiohttp.ClientConnectorError as e:
            raise NetworkError(f"Connection error: {e}")
        except TimeoutError as e:
            raise TimeoutError(f"Request timeout: {e}")
        except Exception as e:
            if isinstance(e, NetworkError):
                raise
            raise NetworkError(f"Request failed: {e}")

    async def request_form(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        token: Optional[str] = None,
    ) -> Response:
        """
        Make form-encoded POST request to Max API (through rate limiter)

        Args:
            path: API endpoint path
            data: Form data
            params: Query parameters
            timeout: Request timeout in seconds
            token: Bot token

        Returns:
            Response object
        """
        return await self.rate_limiter.execute(
            self._do_request_form, path, data, params, timeout, token
        )

    async def _do_request_form(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        token: Optional[str] = None,
    ) -> Response:
        """Internal form request implementation (called through rate limiter)"""
        session = await self._get_session()
        # Support both relative paths and absolute URLs (for callback endpoints)
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self.base_url}{path}"

        headers = {"Authorization": token or self.token or ""}

        logger.info(f"Form request to: {url}, data: {data}")

        try:
            async with session.post(
                url=url,
                data=data,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout or self.default_timeout),
            ) as resp:
                logger.info(f"Response status: {resp.status}")
                response_text = await resp.text()
                logger.debug(f"Response body: {response_text[:500]}")

                try:
                    response_data = await resp.json()
                except:
                    response_data = {"raw": response_text}

                response = Response(
                    ok=resp.status == 200,
                    result=response_data,
                    status_code=resp.status,
                    headers=dict(resp.headers),
                    error=None if resp.status == 200 else f"HTTP {resp.status}",
                )

                if not response.ok:
                    logger.error(f"Error response body: {response_text[:500]}")
                    self._handle_error(response)

                return response

        except aiohttp.ClientConnectorError as e:
            raise NetworkError(f"Connection error: {e}")
        except Exception as e:
            if isinstance(e, NetworkError):
                raise
            raise NetworkError(f"Request failed: {e}")

    def _handle_error(self, response: Response) -> None:
        """Handle error response"""
        error_msg = response.error or "Unknown error"

        if response.status_code == 401:
            raise UnauthorizedError(error_msg, code=response.code, response=response.result)
        elif response.status_code == 403:
            raise ForbiddenError(error_msg, code=response.code, response=response.result)
        elif response.status_code == 404:
            raise NotFoundError(error_msg, code=response.code, response=response.result)
        elif response.status_code == 429:
            retry_after = response.result.get("retry_after", 1) if response.result else 1
            raise RetryAfter(error_msg, retry_after=retry_after)
        else:
            raise ApiError(error_msg, code=response.code, response=response.result)

    async def close(self) -> None:
        """Close HTTP session and rate limiter"""
        await self.rate_limiter.stop()
        if self._session and not self._session.closed and self._close_session:
            await self._session.close()

    async def start(self) -> None:
        """Start rate limiter background tasks"""
        await self.rate_limiter.start()

    async def __aenter__(self) -> "AioScamClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
