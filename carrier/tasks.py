from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command

from carrier.enums import MessageStatus
from carrier.models import Message
from carrier.transports import get_transports

logger = get_task_logger(__name__)


@shared_task
def send_messages():
    call_command('send_messages')


@shared_task
def send_message(message_id):
    logger.info('Sending message {}'.format(message_id))
    transports = get_transports()

    if not transports:
        logger.error('No transports found! Please set CARRIER_TRANSPORT_CLASSES setting.')
        return

    try:
        message = Message.objects.get(pk=message_id)
    except Message.DoesNotExist:
        logger.warning(' Message "{}" does not exist. Skipping.'.format(message_id))
        return

    if message.status not in [MessageStatus.PENDING_INFO, MessageStatus.READY_TO_SEND]:
        logger.warning(' Message "{}" status is not "{}" or "{}". Skipping.'.format(
            message_id, MessageStatus.PENDING_INFO, MessageStatus.READY_TO_SEND))
        return

    message.fetch_contact_info_for_recipients()
    message.attach_contacts_to_recipients()
    message.validate_recipients(transports)
    result = message.send(transports)

    if result.sent:
        logger.info(' Message "{}" Sent.'.format(message_id))
        message.status = MessageStatus.SENT

    if result.errors:
        logger.warning(' Message "{}" Errors: {}.'.format(message_id, ', '.join(result.errors)))
        message.status = MessageStatus.ERROR

    message.save()
