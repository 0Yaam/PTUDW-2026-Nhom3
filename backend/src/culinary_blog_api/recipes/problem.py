from pydantic import BaseModel


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    errors: dict[str, list[str]] | None = None


class RecipeProblem(Exception):
    def __init__(
        self,
        *,
        status: int,
        error_code: str,
        title: str,
        detail: str,
        errors: dict[str, list[str]] | None = None,
    ) -> None:
        self.status = status
        self.error_code = error_code
        self.title = title
        self.detail = detail
        self.errors = errors

    def as_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "type": self.error_code,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
        if self.errors:
            result["errors"] = self.errors
        return result
