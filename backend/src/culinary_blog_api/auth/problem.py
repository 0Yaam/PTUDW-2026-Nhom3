class AuthProblem(Exception):
    def __init__(self, status: int, problem_type: str, title: str, detail: str) -> None:
        self.status = status
        self.problem_type = problem_type
        self.title = title
        self.detail = detail

    def as_dict(self) -> dict[str, str | int]:
        return {
            "type": self.problem_type,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
        }
