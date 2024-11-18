class InputTooLongError(ValueError):
    """Raised when the input is too long."""

    def __init__(self, message="Input is too long"):
        self.message = message
        super().__init__(self.message)


class MaxTurnsExceededError(ValueError):
    """Raised when the maximum number of turns is exceeded."""

    def __init__(self, message="Max turns exceeded"):
        self.message = message
        super().__init__(self.message)
