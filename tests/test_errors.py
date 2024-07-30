from n2y.errors import APIErrorCode


def test_apierrorcode_contains():
    errors = [
        ("bad_gateway", True),
        ("conflict_error", True),
        ("database_connection_unavailable", True),
        ("gateway_timeout", True),
        ("internal_server_error", True),
        ("invalid_grant", False),
        ("invalid_json", False),
        ("invalid_request", False),
        ("invalid_request_url", False),
        ("missing_version", False),
        ("object_not_found", False),
        ("rate_limited", True),
        ("restricted_resource", False),
        ("service_unavailable", True),
        ("unauthorized", False),
        ("validation_error", False),
    ]
    for error, is_retryable in errors:
        assert error in APIErrorCode
        if is_retryable:
            assert (
                error in APIErrorCode.RetryableCodes
                and error not in APIErrorCode.NonRetryableCodes
            )
        else:
            assert (
                error in APIErrorCode.NonRetryableCodes
                and error not in APIErrorCode.RetryableCodes
            )
        assert APIErrorCode(error).is_retryable == is_retryable
        assert APIErrorCode(error).value == error
