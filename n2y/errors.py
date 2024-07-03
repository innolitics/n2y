from enum import StrEnum


class N2YError(Exception):
    pass


class PandocASTParseError(N2YError):
    """
    Raised if there was an error parsing the AST we provided to Pandoc.
    """


class PluginError(N2YError):
    """
    Raised due to various errors loading a plugin.
    """


class UseNextClass(N2YError):
    """
    Used by plugin classes to indicate that the next class should be used instead of them.
    """


class RequestTimeoutError(N2YError):
    """
    Exception for requests that timeout.
    The request that we made waits for a specified period of time or maximum number of
    retries to get the response. But if no response comes within the limited time or
    retries, then this Exception is raised.
    """

    code = "request_timeout"

    def __init__(self, message: str = "Request to Notion API has timed out") -> None:
        super().__init__(message)


class HTTPResponseError(N2YError):
    """
    Exception for HTTP errors.
    Responses from the API use HTTP response codes that are used to indicate general
    classes of success and error.
    """

    def __init__(self, response, message=None) -> None:
        if message is None:
            message = f"Request to Notion API failed with status: {response.status_code}"
        super().__init__(message)
        self.status = response.status_code
        self.headers = response.headers
        self.body = response.text


class APIResponseError(HTTPResponseError):
    """An error raised by Notion API."""

    def __init__(self, response, message, code) -> None:
        super().__init__(response, f"{message} [{code}]")
        self.code = code


class ConnectionThrottled(APIResponseError):
    """
    Raised when the connection is throttled by the Notion API.
    """

    def __init__(self, response, message=None) -> None:
        self.retry_after = (
            float(retry) if (retry := response.headers.get("retry-after")) else 0
        )
        if message is None:
            message = (
                "Your connection has been throttled by the Notion API for"
                f" {self.retry_after} seconds. Please try again later."
            )
        super().__init__(response, message, APIErrorCode.RateLimited)


class ObjectNotFound(APIResponseError):
    def __init__(self, response, message) -> None:
        super().__init__(response, message, APIErrorCode.ObjectNotFound)


class APIErrorCode(StrEnum):
    def __new__(cls, code, is_retryable):
        obj = str.__new__(cls, code)
        obj._value_ = str(code)
        obj.is_retryable = is_retryable
        cls.RetryableCodes = [i.value for i in cls if i.is_retryable is True]
        cls.NonretryableCodes = [i.value for i in cls if i.is_retryable is True]
        return obj

    BadGateway = "bad_gateway", True
    """Notion encountered an issue while attempting to complete this request.
    Please try again."""

    ConflictError = "conflict_error", True
    """The transaction could not be completed, potentially due to a data collision.
    Make sure the parameters are up to date and try again."""

    DatabaseConnectionUnavailable = "database_connection_unavailable", True
    """Notion's database is unavailable or in an unqueryable state. Try again later."""

    GatewayTimeout = "gateway_timeout", True
    """Notion timed out while attempting to complete this request.
    Please try again later."""

    InternalServerError = "internal_server_error", True
    """An unexpected error occurred. Reach out to Notion support."""

    InvalidGrant = "invalid_grant", False
    """The authorization code or refresh token is not valid."""

    InvalidJSON = "invalid_json", False
    """The request body could not be decoded as JSON."""

    InvalidRequest = "invalid_request", False
    """This request is not supported."""

    InvalidRequestURL = "invalid_request_url", False
    """The request URL is not valid."""

    MissingVersion = "missing_version", False
    """The request is missing the required Notion-Version header"""

    ObjectNotFound = "object_not_found", False
    """Given the bearer token used, the resource does not exist.
    This error can also indicate that the resource has not been shared with owner
    of the bearer token."""

    RateLimited = "rate_limited", True
    """The client has sent too many requests in a given amount of time."""

    RestrictedResource = "restricted_resource", False
    """Given the bearer token used, the client doesn't have permission to
    perform this operation."""

    ServiceUnavailable = "service_unavailable", True
    """Notion is unavailable. Try again later. This can occur when the time to respond
    to a request takes longer than 60 seconds, the maximum request timeout."""

    Unauthorized = "unauthorized", False
    """The bearer token is not valid."""

    ValidationError = "validation_error", False
    """The request body does not match the schema for the expected parameters."""


# Some of this code was taken from https://github.com/ramnes/notion-sdk-py
"""
The MIT License (MIT)

Copyright (c) 2021 Guillaume Gelin

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
