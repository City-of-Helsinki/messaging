import argparse
import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.utils import timezone

from carrier.enums import RecipientStatus
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
            message_ids = list(Message.objects.filter(status=MessageStatus.READY_TO_SEND).order_by(
                'created_at').values_list('id', flat=True))

        if not message_ids:
            self.stdout.write('No messages to send.')
            return

        # Transports
        transports = get_transports()

        if not transports:
            self.stdout.write(self.style.ERROR('No transports found! Please set CARRIER_TRANSPORT_CLASSES setting.'))
            return

        # Messages
        for message_id in message_ids:
            self.stdout.write('Message "{}":'.format(message_id))
            try:
                message = Message.objects.get(pk=message_id)
            except Message.DoesNotExist:
                self.stdout.write(self.style.WARNING('Message "{}" does not exist. Skipping.'.format(message_id)))
                continue

            (sendable, errors) = message.is_sendable()

            if not sendable:
                self.stdout.write(self.style.WARNING('Message is not sendable. Errors: {}'.format(','.join(errors))))
                continue

            message.status = MessageStatus.SENDING
            message.save()

            transport_recipients = defaultdict(list)
            for recipient in message.recipients.filter(status=RecipientStatus.READY_TO_SEND):
                found = False

                for transport in transports:
                    # Use the first suitable transport
                    if transport.is_suitable_for_recipient(recipient):
                        transport_recipients[transport].append(recipient)
                        found = True
                        break

                if not found:
                    self.stdout.write(self.style.WARNING(
                        'No suitable transport found for recipient id {}. Skipping.'.format(recipient.id)))

            errors = []
            for transport, recipients in transport_recipients.items():
                result = transport.send(message, recipients)
                errors.extend(result['errors'])

            message.sent_at = timezone.now()

            if not errors:
                self.stdout.write(self.style.SUCCESS('Message "{}" sent'.format(message_id)))
                message.status = MessageStatus.SENT
            else:
                self.stdout.write(self.style.SUCCESS('Message "{}" processed with errors: {}'.format(
                    message_id, errors)))
                message.status = MessageStatus.ERROR

            message.save()
