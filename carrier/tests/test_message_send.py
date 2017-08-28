import pytest

from carrier.enums import MessageStatus, RecipientStatus
from carrier.models import MessageSendResult
from carrier.transports import TransportBase


class SuccessTransport(TransportBase):
    def is_valid(self):
        return True

    def is_suitable_for_recipient(self, recipient):
        return True

    def send(self, message, recipients):
        return {
            "success": True,
            "errors": [],
        }


class FailTransport(TransportBase):
    def is_valid(self):
        return True

    def is_suitable_for_recipient(self, recipient):
        return True

    def send(self, message, recipients):
        return {
            "success": False,
            "errors": ['Error'],
        }


@pytest.mark.django_db
def test_empty_message_fail(message_factory):
    transport = SuccessTransport()
    message = message_factory()
    result = message.send([transport])

    assert isinstance(result, MessageSendResult)
    assert result.has_errors() is True
    assert result.sent is False


@pytest.mark.django_db
def test_message_fail(settings, message_factory, recipient_factory, content_factory):
    settings.CARRIER_CONTENT_LANGUAGES = ['cc', 'dd', 'ee']

    transports = [FailTransport()]
    message = message_factory(status=MessageStatus.READY_TO_SEND)
    content_factory(message=message, language="cc", subject="Subject", text="Text")
    recipient_factory(message=message, email="test@example.com")

    message.validate_recipients(transports)
    result = message.send(transports)

    assert isinstance(result, MessageSendResult)
    assert message.recipients.first().status == RecipientStatus.READY_TO_SEND
    assert result.has_errors() is True
    assert result.sent is True


@pytest.mark.django_db
def test_success(settings, message_factory, recipient_factory, content_factory):
    settings.CARRIER_CONTENT_LANGUAGES = ['cc', 'dd', 'ee']

    transports = [SuccessTransport()]
    message = message_factory(status=MessageStatus.READY_TO_SEND)
    content_factory(message=message, language="cc", subject="Subject", text="Text")
    recipient_factory(message=message, email="test@example.com")

    message.validate_recipients(transports)
    result = message.send(transports)

    assert isinstance(result, MessageSendResult)
    assert result.has_errors() is False
    assert result.sent is True
