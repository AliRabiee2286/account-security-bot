"""Headers for secret-bearing one-time forms. Never cache or leak URL referrer."""

from fastapi import Response


def secure_form_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    )
