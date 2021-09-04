class SemoxyValidationError(ValueError):
    """
    exception that is raised from custom model validators for displaying an error message to the user
    """
    def __init__(self, field, description):
        self.field = field
        self.description = description
