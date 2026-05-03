"""Application-specific exception hierarchy."""


class PackageGoException(Exception):
    """Base exception for all PackageGo business errors."""

    def __init__(self, detail: str, status_code: int = 500):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class NotFoundException(PackageGoException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail=detail, status_code=404)


class BadRequestException(PackageGoException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(detail=detail, status_code=400)


class ConflictException(PackageGoException):
    def __init__(self, detail: str = "Conflict"):
        super().__init__(detail=detail, status_code=409)


class ForbiddenException(PackageGoException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(detail=detail, status_code=403)


class UnauthorizedException(PackageGoException):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(detail=detail, status_code=401)
