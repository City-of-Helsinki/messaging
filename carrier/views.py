import random
import string
import uuid

from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'], exclude_from_schema=True)
@permission_classes([AllowAny])
def get_contact_info(request):
    """Fake contact info endpoint for development purposes."""
    if 'ids' not in request.GET or not request.GET['ids']:
        raise ValidationError("Please provide the ids")

    id_strings = [part.strip() for part in request.GET['ids'].split(',')]

    contact_info = {}
    for id_string in id_strings:
        try:
            user_uuid = uuid.UUID(id_string)
        except ValueError:
            contact_info[id_string] = {
                "error": "Invalid user id",
            }
            continue

        contact_info[user_uuid] = {
            "email": "{}@example.com".format(''.join(
                random.choice(string.ascii_lowercase) for _ in range(8))),
            "phone": "+358401234567",
            "language": random.choice(["fi", "sv", "en"]),
            "contact_method": "email",
        }

    return Response(contact_info)
