import json

import pytest

from carrier.enums import MessageStatus
from carrier.serializers import MessageSerializer


@pytest.mark.django_db
def test_create_message():
    data = """{
        "from": {
            "name": "John Doe",
            "email": "john@example.com"
        },
        "recipients": [
            {
                "uuid": "a2f57e4a-2796-42fa-b85b-900c0e4bbcd6"
            },
            {
                "email": "test1@example.com"
            }
        ],
        "contents": [
            {
                "language": "fi",
                "subject": "Test subject fi",
                "text": "Test text fi",
                "html": "Test html fi",
                "short_text": "Test short text fi"
            },
            {
                "language": "sv",
                "subject": "Test subject sv",
                "text": "Test text sv",
                "html": "Test html sv",
                "short_text": "Test short text sv"
            }
        ]
    }"""

    serializer = MessageSerializer(data=json.loads(data))

    assert serializer.is_valid(raise_exception=True)
    instance = serializer.save()

    assert instance.id
    assert instance.status == MessageStatus.PENDING_INFO
    assert len(instance.recipients.all()) == 2
    assert len(instance.contents.all()) == 2
