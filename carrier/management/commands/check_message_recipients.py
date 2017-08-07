import argparse
import re

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from requests import RequestException

from carrier.enums import RecipientStatus
from carrier.models import Contact, Message, MessageStatus


def is_uuidv4(val):
    regex = re.compile('^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', re.I)
    match = regex.match(val)

    if not match:
        raise argparse.ArgumentTypeError("Invalid UUID")

    return val


class Command(BaseCommand):
    help = 'Checks that all the message recipients have an associated contact if applicable.'

    def add_arguments(self, parser):
        parser.add_argument('message_id', nargs='*', type=is_uuidv4)

    def handle(self, *args, **options):
        if options['message_id']:
            message_ids = options['message_id']
        else:
            message_ids = list(Message.objects.filter(status=MessageStatus.PENDING_INFO).order_by(
                'created_at').values_list('id', flat=True))

        if not message_ids:
            self.stdout.write('No messages to go through.')
            return

        # Messages
        for message_id in message_ids:
            self.stdout.write('Message "{}":'.format(message_id))
            try:
                message = Message.objects.get(pk=message_id)
            except Message.DoesNotExist:
                self.stdout.write(self.style.WARNING('Message "{}" does not exist. Skipping.'.format(message_id)))
                continue

            if message.status != MessageStatus.PENDING_INFO:
                self.stdout.write(
                    self.style.WARNING('Status for message "{}" is not "{}", but "{}". Skipping.'.format(
                        message_id, MessageStatus.PENDING_INFO, message.status)))
                continue

            if message.recipients.count() == 0:
                self.stdout.write(self.style.WARNING(
                    'Message "{}" has no recipients. Skipping.'.format(message_id)))
                continue

            message.status = MessageStatus.FETCHING_INFO
            message.save()

            # Gather ids that we need to get contact info for
            recipient_uuids = [str(v) for v in message.recipients.filter(
                uuid__isnull=False, contact__isnull=True).values_list('uuid', flat=True)]

            if recipient_uuids:
                url = '{}?ids={}'.format(settings.CONTACT_INFO_URL, ','.join(recipient_uuids))

                try:
                    r = requests.get(url)
                    r.raise_for_status()

                    for contact_id, contact_info in r.json().items():
                        Contact.objects.filter(id=contact_id).delete()

                        contact = Contact.objects.create(
                            id=contact_id,
                            email=contact_info.get('email'),
                            phone=contact_info.get('phone'),
                            language=contact_info.get('language'),
                            preferred_transport=contact_info.get('contact_method')
                        )

                        message.recipients.filter(uuid=contact_id).update(contact=contact)
                except RequestException:
                    self.stdout.write(self.style.ERROR('Error when fetching contact info for ids "{}"'.format(
                        ','.join(recipient_uuids))))
                    continue

            # TODO: Think about this
            # Check all recipients
            all_ok = True
            for recipient in message.recipients.all():
                if recipient.contact or recipient.email or recipient.phone:
                    recipient.status = RecipientStatus.READY_TO_SEND
                    recipient.save()
                else:
                    all_ok = False

            if all_ok:
                message.status = MessageStatus.READY_TO_SEND
                self.stdout.write(self.style.SUCCESS('Ready to send'))
            else:
                message.status = MessageStatus.PENDING_INFO
                self.stdout.write(self.style.WARNING('Not ready to send'))

            message.save()
