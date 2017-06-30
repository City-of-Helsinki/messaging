from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class RecipientStatus(Enum):
    PENDING = 'pending'
    SENT = 'sent'
    ERROR = 'error'

    class Labels:
        PENDING = _('Pending')
        SENT = _('Sent')
        ERROR = _('Error')


class MessageStatus(Enum):
    PENDING = 'pending'
    PROCESSED = 'processed'
    ERROR = 'error'
    ARCHIVED = 'archived'

    class Labels:
        PENDING = _('Pending')
        PROCESSED = _('Processed')
        ERROR = _('Error')
        ARCHIVED = _('Archived')
