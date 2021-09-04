class SemoxyValidationError(Exception):
    def __init__(self, field, description):
        self.field = field
        self.description = description
