from src.core.errors import ApplicationError


class MenuNotFoundError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=404,
            code="MENU_NOT_FOUND",
            message="Menu was not found.",
        )


class MenuForbiddenError(ApplicationError):
    def __init__(self) -> None:
        super().__init__(
            status_code=403,
            code="FORBIDDEN",
            message="You do not have access to this menu.",
        )
