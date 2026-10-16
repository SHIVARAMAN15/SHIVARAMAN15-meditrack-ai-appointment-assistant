"""
Custom application exception classes for structured error handling.
"""

class AppException(Exception):
    """Base application exception."""
    status_code = 500
    code = "INTERNAL_ERROR"

    def __init__(self, message: str, code: str = None, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.details = details or {}

    def to_dict(self):
        result = {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result


class ValidationError(AppException):
    status_code = 400
    code = "VALIDATION_ERROR"


class NotFoundError(AppException):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppException):
    status_code = 409
    code = "CONFLICT_ERROR"


class BusinessRuleError(AppException):
    status_code = 422
    code = "BUSINESS_RULE_VIOLATION"


class ModelNotReadyError(AppException):
    status_code = 503
    code = "MODEL_NOT_READY"
