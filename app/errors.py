from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

# user-friendly error messages
ERROR_MESSAGES = {
    400: "Something went wrong with your request. Please check your input and try again.",
    401: "You need to be authenticated to access this resource.",
    403: "You don't have permission to access this resource.",
    404: "The resource you're looking for doesn't exist.",
    413: "The file you're trying to upload is too large.",
    415: "This file type isn't supported. Please use MP3, MP4, WAV, M4A, WebM, or OGG.",
    429: "You're making too many requests. Please wait a moment and try again.",
    500: "Something went wrong on our end. Please try again later.",
    502: "We're having trouble connecting to our services. Please try again.",
    503: "The service is temporarily unavailable. Please try again in a few minutes.",
}


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors with a friendly message."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "You're making requests too quickly. Please wait a moment and try again.",
            "retry_after": str(exc.detail).split("per")[0].strip() if exc.detail else "1 minute"
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Custom handler for HTTP exceptions with friendlier messages.
    Preserves specific error messages when provided.
    """
    # if the exception has a specific detail, use it
    # otherwise fall back to our friendly messages
    if exc.detail and exc.detail != "Not Found" and exc.detail != "Internal Server Error":
        message = exc.detail
    else:
        message = ERROR_MESSAGES.get(exc.status_code, "An unexpected error occurred.")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": get_error_code(exc.status_code),
            "message": message,
            "status_code": exc.status_code
        }
    )


def get_error_code(status_code: int) -> str:
    """Convert status code to a readable error code."""
    codes = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        413: "file_too_large",
        415: "unsupported_file_type",
        429: "rate_limit_exceeded",
        500: "internal_error",
        502: "bad_gateway",
        503: "service_unavailable",
    }
    return codes.get(status_code, "error")
