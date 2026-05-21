from fastapi import HTTPException


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


def upstream_error(detail: str) -> HTTPException:
    return HTTPException(status_code=502, detail=detail)
