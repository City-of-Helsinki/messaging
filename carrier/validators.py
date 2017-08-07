from rest_framework.exceptions import ValidationError


class OrValidator:
    def __init__(self, fields):
        self.fields = fields
        self.instance = None

    def set_context(self, serializer):
        self.instance = getattr(serializer, 'instance', None)

    def __call__(self, attrs):
        instance = self.instance if self.instance else {}

        values = []
        for field in self.fields:
            values.append(attrs[field] if field in attrs else getattr(instance, field, None))

        if not any(values):
            field_names = ', '.join(self.fields)
            message = 'At least one of the fields "{}" must have value.'.format(field_names)

            raise ValidationError(message, code='required')

    def __repr__(self):
        return '<%s(fields=%s)>'.format(self.__class__.__name__, self.fields)
