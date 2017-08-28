import uuid

import pytest
from django.utils.crypto import get_random_string

from carrier.enums import RecipientStatus
from carrier.models import Recipient


@pytest.mark.django_db
@pytest.mark.parametrize('field_name', ['email', 'phone', 'language'])
def test_get_field_value_from_recipient(message_factory, contact_factory, recipient_factory, field_name):
    message = message_factory()
    recipient = recipient_factory(message=message, status=RecipientStatus.READY_TO_SEND)
    setattr(recipient, field_name, get_random_string())

    assert getattr(recipient, 'get_{}'.format(field_name))() == getattr(recipient, field_name)


@pytest.mark.django_db
@pytest.mark.parametrize('field_name', ['email', 'phone', 'language'])
def test_get_field_value_from_contact(message_factory, contact_factory, recipient_factory, field_name):
    message = message_factory()
    contact = contact_factory()
    setattr(contact, field_name, get_random_string())
    recipient = recipient_factory(contact=contact, message=message, status=RecipientStatus.READY_TO_SEND)

    assert getattr(recipient, 'get_{}'.format(field_name))() == getattr(contact, field_name)


@pytest.mark.django_db
@pytest.mark.parametrize('field_name', ['email', 'phone', 'language'])
def test_get_field_value_from_recipient_override(message_factory, contact_factory, recipient_factory, field_name):
    message = message_factory()

    contact = contact_factory()
    setattr(contact, field_name, get_random_string())

    recipient = recipient_factory(contact=contact, message=message, status=RecipientStatus.READY_TO_SEND)
    setattr(recipient, field_name, get_random_string())

    assert getattr(recipient, 'get_{}'.format(field_name))() == getattr(recipient, field_name)


@pytest.mark.django_db
def test_get_language_fallback(settings, message_factory, contact_factory, recipient_factory):
    settings.CARRIER_CONTENT_LANGUAGES = ['bb', 'cc', 'dd']

    message = message_factory()
    recipient = recipient_factory(message=message, status=RecipientStatus.READY_TO_SEND)

    assert recipient.get_language() == "bb"

    contact = contact_factory()
    recipient.contact = contact

    assert recipient.get_language() == "bb"


@pytest.mark.django_db
def test_get_pushbullet_access_token(message_factory, contact_factory, recipient_factory):
    message = message_factory()
    contact = contact_factory()
    recipient = recipient_factory(contact=contact, message=message, status=RecipientStatus.READY_TO_SEND)
    contact.pushbullet_access_token = get_random_string()

    assert recipient.get_pushbullet_access_token() == contact.pushbullet_access_token


@pytest.mark.django_db
def test_get_pushbullet_access_token_empty(message_factory, contact_factory, recipient_factory):
    message = message_factory()
    contact = contact_factory()
    recipient = recipient_factory(contact=contact, message=message, status=RecipientStatus.READY_TO_SEND)

    assert recipient.get_pushbullet_access_token() is None


@pytest.mark.django_db
def test_contact_no_attach_on_save(message_factory):
    message = message_factory()
    recipient = Recipient.objects.create(message=message)

    assert recipient.contact is None


@pytest.mark.django_db
def test_contact_attach_on_save(message_factory, contact_factory):
    message = message_factory()
    contact = contact_factory(id=uuid.uuid4())
    recipient = Recipient.objects.create(message=message, uuid=contact.id)

    assert recipient.contact == contact
