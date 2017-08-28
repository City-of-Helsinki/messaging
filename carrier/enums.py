from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class RecipientStatus(Enum):
    PENDING_INFO = 'pending_info'
    READY_TO_SEND = 'ready_to_send'
    IGNORED = 'ignored'
    SENDING = 'sending'
    SENT = 'sent'
    ERROR = 'error'

    class Labels:
        PENDING_INFO = _('Pending information')
        READY_TO_SEND = _('Ready to send')
        IGNORED = _('Ignored')
        SENDING = _('Sending')
        SENT = _('Sent')
        ERROR = _('Error')


class MessageStatus(Enum):
    PENDING_INFO = 'pending_info'
    FETCHING_INFO = 'fetching_info'
    READY_TO_SEND = 'ready_to_send'
    SENDING = 'sending'
    SENT = 'sent'
    ERROR = 'error'
    ARCHIVED = 'archived'

    class Labels:
        PENDING_INFO = _('Pending information')
        FETCHING_INFO = _('Fetching information')
        SENDING = _('Sending')
        SENT = _('Sent')
        ERROR = _('Error')
        ARCHIVED = _('Archived')


class TransportType(Enum):
    EMAIL = 'email'
    PUSHBULLET = 'pushbullet'
    SMS = 'sms'

    class Labels:
        EMAIL = _('Email')
        PUSHBULLET = _('Pushbullet')
        SMS = _('SMS')
