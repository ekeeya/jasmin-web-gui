from rest_framework.validators import UniqueValidator


class JoyceUniqueFieldValidator(UniqueValidator):
    """
        A custom UniqueValidator that skips validation if the value matches the current instance's value.
    """

    def __init__(self, queryset, message=None, lookup='exact'):
        super().__init__(queryset=queryset, message=message, lookup=lookup)
        self.instance = None  # Will be set by the serializer

    def __call__(self, value, serializer_field):
        # Get the instance from the serializer's context
        serializer = serializer_field.parent
        self.instance = getattr(serializer, 'instance', None)

        if self.instance is not None:
            # Get the current value of the field from the instance
            field_name = serializer_field.field_name
            current_value = getattr(self.instance, field_name, None)

            # If the value matches the instance's current value, skip validation
            if current_value == value:
                return

        # Proceed with the default uniqueness validation
        super().__call__(value, serializer_field)