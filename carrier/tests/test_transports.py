import pytest

from carrier.transports import TransportBase, get_transports


class TestTransport(TransportBase):
    def is_valid(self):
        return True

    def is_suitable_for_recipient(self, recipient):
        return True

    def send(self, message, recipients):
        return {
            "success": True,
            "errors": [],
        }


class TestTransport2(TransportBase):
    def is_valid(self):
        return True

    def is_suitable_for_recipient(self, recipient):
        return True

    def send(self, message, recipients):
        return {
            "success": True,
            "errors": [],
        }


def test_get_transports(settings):
    settings.CARRIER_TRANSPORT_CLASSES = [
        'carrier.tests.test_transports.TestTransport',
        'carrier.tests.test_transports.TestTransport2',
    ]

    transports = get_transports()

    assert len(transports) == 2
    assert isinstance(transports[0], TestTransport)
    assert isinstance(transports[1], TestTransport2)


def test_get_transports_fail(settings):
    settings.CARRIER_TRANSPORT_CLASSES = [
        'carrier.tests.test_transports.NonexistingTransport',
    ]

    with pytest.raises(ImportError):
        get_transports()
