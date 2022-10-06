from enum import Enum


class N2YError(Exception):
    pass


class PandocASTParseError(N2YError):
    """
    Raised if there was an error parsing the AST we provided to Pandoc.
    """
    pass


class PluginError(N2YError):
    """
    Raised due to various errors loading a plugin.
    """
    pass


class UseNextClass(Exception):
    """
    Used by plugin classes to indicate that the next class should be used instead of them.
    """
    pass


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
            message = (
                f"Request to Notion API failed with status: {response.status_code}"
            )
        super().__init__(message)
        self.status = response.status_code
        self.headers = response.headers
        self.body = response.text


class APIErrorCode(str, Enum):
    Unauthorized = "unauthorized"
    """The bearer token is not valid."""

    RestrictedResource = "restricted_resource"
    """Given the bearer token used, the client doesn't have permission to
    perform this operation."""

    ObjectNotFound = "object_not_found"
    """Given the bearer token used, the resource does not exist.
    This error can also indicate that the resource has not been shared with owner
    of the bearer token."""

    RateLimited = "rate_limited"
    """This request exceeds the number of requests allowed. Slow down and try again."""

    InvalidJSON = "invalid_json"
    """The request body could not be decoded as JSON."""

    InvalidRequestURL = "invalid_request_url"
    """The request URL is not valid."""

    InvalidRequest = "invalid_request"
    """This request is not supported."""

    ValidationError = "validation_error"
    """The request body does not match the schema for the expected parameters."""

    ConflictError = "conflict_error"
    """The transaction could not be completed, potentially due to a data collision.
    Make sure the parameters are up to date and try again."""

    InternalServerError = "internal_server_error"
    """An unexpected error occurred. Reach out to Notion support."""

    ServiceUnavailable = "service_unavailable"
    """Notion is unavailable. Try again later.
    This can occur when the time to respond to a request takes longer than 60 seconds,
    the maximum request timeout."""


class APIResponseError(HTTPResponseError):
    """An error raised by Notion API."""

    def __init__(self, response, message, code) -> None:
        super().__init__(response, f"{message} [{code}]")
        self.code = code


class ObjectNotFound(APIResponseError):
    def __init__(self, response, message) -> None:
        code = APIErrorCode.ObjectNotFound
        super().__init__(response, f"{message} [{code}]", code)
        self.code = code


def is_api_error_code(code: str) -> bool:
    """Check if given code belongs to the list of valid API error codes."""
    if isinstance(code, str):
        return code in (error_code.value for error_code in APIErrorCode)
    return False


# Some of this code was taken from https://github.com/ramnes/notion-sdk-py
'''
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
'''
