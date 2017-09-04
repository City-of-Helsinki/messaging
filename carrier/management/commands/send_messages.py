import argparse
import re

from django.core.management.base import BaseCommand

from carrier.models import Message, MessageStatus
from carrier.transports import get_transports


def is_uuidv4(val):
    regex = re.compile('^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', re.I)
    match = regex.match(val)

    if not match:
        raise argparse.ArgumentTypeError("Invalid UUID")

    return val


class Command(BaseCommand):
    help = 'Sends messages'

    def add_arguments(self, parser):
        parser.add_argument('message_id', nargs='*', type=is_uuidv4)

    def handle(self, *args, **options):
        if options['message_id']:
            message_ids = options['message_id']
        else:
            message_ids = list(Message.objects.filter(
                status__in=[MessageStatus.PENDING_INFO, MessageStatus.READY_TO_SEND]).order_by(
                'created_at').values_list('id', flat=True))

        if not message_ids:
            self.stdout.write('No messages to send.')
            return

        transports = get_transports()

        if not transports:
            self.stdout.write(self.style.ERROR('No transports found! Please set CARRIER_TRANSPORT_CLASSES setting.'))
            return

        for message_id in message_ids:
            self.stdout.write('Message "{}":'.format(message_id))
            try:
                message = Message.objects.get(pk=message_id)
            except Message.DoesNotExist:
                self.stdout.write(self.style.WARNING(' Message "{}" does not exist. Skipping.'.format(message_id)))
                continue

            if message.status not in [MessageStatus.PENDING_INFO, MessageStatus.READY_TO_SEND]:
                self.stdout.write(self.style.WARNING(
                    ' Message "{}" status is not "{}" or "{}". Skipping.'.format(message_id, MessageStatus.PENDING_INFO,
                        MessageStatus.READY_TO_SEND)))
                continue

            message.fetch_contact_info_for_recipients()
            message.attach_contacts_to_recipients()
            message.validate_recipients(transports)
            result = message.send(transports)

            if result.sent:
                self.stdout.write(self.style.WARNING(' Message "{}" Sent.'.format(message_id)))
                message.status = MessageStatus.SENT

            if result.errors:
                self.stdout.write(self.style.WARNING(' Errors: ' + ', '.join(result.errors)))
                message.status = MessageStatus.ERROR

            message.save()
