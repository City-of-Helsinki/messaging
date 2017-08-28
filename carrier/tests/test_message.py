import json
import uuid

import pytest
import requests_mock

from carrier.enums import MessageStatus, RecipientStatus
from carrier.models import Contact
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


@pytest.mark.django_db
def test_empty_message_is_not_sendable(message_factory):
    message = message_factory()

    assert message.is_sendable() is False


@pytest.mark.django_db
def test_message_without_content_or_recipients_is_not_sendable(message_factory):
    message = message_factory(status=MessageStatus.READY_TO_SEND)

    assert message.is_sendable() is False


@pytest.mark.django_db
def test_message_without_content_is_not_sendable(message_factory, recipient_factory):
    message = message_factory(status=MessageStatus.READY_TO_SEND)
    recipient_factory(message=message, status=RecipientStatus.READY_TO_SEND)

    assert message.is_sendable() is False


@pytest.mark.django_db
def test_message_without_recipients_is_not_sendable(message_factory, content_factory):
    message = message_factory(status=MessageStatus.READY_TO_SEND)
    content_factory(message=message)

    assert message.is_sendable() is False


@pytest.mark.django_db
def test_message_is_sendable(message_factory, recipient_factory, content_factory):
    message = message_factory(status=MessageStatus.READY_TO_SEND)
    recipient_factory(message=message, status=RecipientStatus.READY_TO_SEND)
    content_factory(message=message)

    assert message.is_sendable() is True


@pytest.mark.django_db
def test_message_get_content_languages(message_factory, content_factory):
    message = message_factory(status=MessageStatus.READY_TO_SEND)
    content_factory(message=message, language="fi")
    content_factory(message=message, language="en")

    assert message.get_content_languages() == {"en", "fi"}


@pytest.mark.django_db
def test_message_get_content_in_language(message_factory, content_factory):
    message = message_factory(status=MessageStatus.READY_TO_SEND)
    content_factory(message=message, language="fi")
    content_en = content_factory(message=message, language="en")

    content = message.get_content_in_language("en")

    assert content.language == 'en'
    assert content == content_en


@pytest.mark.django_db
def test_message_get_content_in_language_fallback(settings, message_factory, content_factory):
    settings.CARRIER_CONTENT_LANGUAGES = ['cc', 'dd', 'ee']

    message = message_factory(status=MessageStatus.READY_TO_SEND)
    content_cc = content_factory(message=message, language="cc")
    content_factory(message=message, language="dd")

    content = message.get_content_in_language("ff")

    assert content.language == "cc"
    assert content == content_cc

    settings.CARRIER_CONTENT_LANGUAGES = ['dd', 'cc', 'ee']

    assert message.get_content_in_language("ff").language == "dd"


@pytest.mark.django_db
def test_fetch_contact_info_for_recipients(settings, message_factory, recipient_factory, contact_factory):
    settings.CONTACT_INFO_URL = 'http://example.com/'

    contact_uuid = uuid.uuid4()

    message = message_factory(status=MessageStatus.PENDING_INFO)
    recipient1 = recipient_factory(message=message, uuid=contact_uuid)

    with requests_mock.Mocker() as m:
        url = '{}?ids={}'.format(settings.CONTACT_INFO_URL, contact_uuid)

        data = {
            str(contact_uuid): {
                "email": "test1@example.com",
                "pushbullet": None,
                "phone": "+358123456789",
                "language": "fi",
                "contact_method": "email"
            }
        }

        m.get(url, json=data)

        message.fetch_contact_info_for_recipients()

    assert Contact.objects.get(pk=contact_uuid).email == "test1@example.com"

    message.attach_contacts_to_recipients()

    assert message.recipients.get(pk=recipient1.id).contact.email == "test1@example.com"
