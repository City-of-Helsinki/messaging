import json
from collections import defaultdict
from importlib import import_module

import requests
from django.conf import settings
from pyfcm import FCMNotification
from requests import RequestException

from carrier.enums import RecipientStatus, TransportType


class TransportBase:
    def is_valid(self):
        raise NotImplementedError('Method "valid" must be implemented.')

    def is_suitable_for_recipient(self, recipient):
        raise NotImplementedError('Method "is_suitable_for_recipient" must be implemented.')

    def send(self, message, recipients):
        raise NotImplementedError('Method send must be implemented.')


class MailGunTransport(TransportBase):
    def __init__(self):
        self.transport_type = TransportType.EMAIL

    def is_valid(self):
        if getattr(settings, 'MAILGUN_DOMAIN', None) and getattr(settings, 'MAILGUN_API_KEY', None):
            return True

        return False

    def is_suitable_for_recipient(self, recipient):
        return bool(recipient.get_email())

    def send(self, message, recipients):
        recipients_by_language = defaultdict(list)
        for recipient in recipients:
            recipients_by_language[recipient.get_language()].append(recipient)

        errors = []
        for language, lang_recipients in recipients_by_language.items():
            content = message.get_content_in_language(language)

            # Make Mailgun send a separate email to every recipient by using the Recipient Variables functionality.
            # See http://mailgun-documentation.readthedocs.io/en/latest/user_manual.html#batch-sending
            recipient_variables = {r.get_email(): {"id": r.id} for r in lang_recipients}

            data = {
                "from": "{} <{}>".format(message.from_name, message.from_email),
                "to": [recipient.get_email() for recipient in lang_recipients],
                "subject": content.subject,
                "text": content.text,
                "recipient-variables": json.dumps(recipient_variables),
            }
            if content.html:
                data['html'] = content.html

            message.recipients.filter(id__in=[recipient.id for recipient in lang_recipients]).update(
                status=RecipientStatus.SENDING)

            try:
                # TODO: Make requests in 1000 recipient batches
                r = requests.post(
                    "https://api.mailgun.net/v3/{}/messages".format(settings.MAILGUN_DOMAIN),
                    auth=("api", settings.MAILGUN_API_KEY),
                    data=data
                )

                r.raise_for_status()

                for recipient in lang_recipients:
                    recipient.transport = self.transport_type
                    recipient.language = language
                    recipient.email = recipient.get_email()
                    recipient.status = RecipientStatus.SENT
                    recipient.save()
            except RequestException as e:
                errors.append('Error when trying to send message "{}", content "{}" to {} recipient(s): "{}"'.format(
                    message.id, content.id, len(lang_recipients), e))

        return {
            "success": not bool(errors),
            "errors": errors,
        }


class DummySmsTransport(TransportBase):
    def __init__(self):
        self.transport_type = TransportType.SMS

    def is_valid(self):
        return True

    def is_suitable_for_recipient(self, recipient):
        return bool(recipient.get_phone())

    def send(self, message, recipients):
        print("Send message {} using transport DummySmsTransport to recipients: {}".format(message.id, recipients))

        content = message.get_content_in_language(None)

        for recipient in recipients:
            recipient.transport = self.transport_type
            recipient.lang = content.language
            recipient.phone = recipient.get_phone()
            recipient.status = RecipientStatus.SENT
            recipient.save()

        return {
            "success": True,
            "errors": [],
        }


class PushbulletTransport(TransportBase):
    def __init__(self):
        self.transport_type = TransportType.PUSHBULLET

    def is_valid(self):
        return True

    def is_suitable_for_recipient(self, recipient):
        return bool(recipient.get_pushbullet_access_token())

    def send(self, message, recipients):
        errors = []
        for recipient in recipients:
            content = message.get_content_in_language(recipient.get_language())

            text = content.short_text if content.short_text else content.text

            try:
                r = requests.post('https://api.pushbullet.com/v2/pushes', json={
                    'body': text,
                    'title': content.subject,
                    'type': 'note',
                }, headers={
                    'Access-Token': recipient.get_pushbullet_access_token(),
                    'Content-Type': 'application/json'
                })

                r.raise_for_status()

                recipient.transport = self.transport_type
                recipient.lang = content.language
                recipient.status = RecipientStatus.SENT
                recipient.save()
            except RequestException as e:
                errors.append(
                    'Error when trying to send message "{}", content "{}" to {} recipient(s): "{}"'.format(
                        message.id, content.id, recipients, e))

        return {
            "success": not bool(errors),
            "errors": errors,
        }


class FirebaseMessagingTransport(TransportBase):
    def __init__(self):
        self.transport_type = TransportType.FIREBASE

    def is_valid(self):
        if getattr(settings, 'FIREBASE_API_KEY', None):
            return True

        return False

    def is_suitable_for_recipient(self, recipient):
        return bool(recipient.get_firebase_token())

    def send(self, message, recipients):
        recipients_by_language = defaultdict(list)
        for recipient in recipients:
            recipients_by_language[recipient.get_language()].append(recipient)

        push_service = FCMNotification(api_key=settings.FIREBASE_API_KEY)

        errors = []
        for language, lang_recipients in recipients_by_language.items():
            content = message.get_content_in_language(language)

            message.recipients.filter(id__in=[recipient.id for recipient in lang_recipients]).update(
                status=RecipientStatus.SENDING)

            registration_ids = [r.get_firebase_token() for r in lang_recipients]

            result = push_service.notify_multiple_devices(
                registration_ids=registration_ids, message_title=content.subject, message_body=content.text)

            # TODO: check result

            for recipient in lang_recipients:
                recipient.transport = self.transport_type
                recipient.language = language
                recipient.status = RecipientStatus.SENT
                recipient.save()

        return {
            "success": not bool(errors),
            "errors": errors,
        }


def get_transports():
    transports = []
    for transport_class_string in settings.CARRIER_TRANSPORT_CLASSES:
        try:
            parts = transport_class_string.split('.')
            module_path, class_name = '.'.join(parts[:-1]), parts[-1]
            module_name = import_module(module_path)

            transport_class = getattr(module_name, class_name)
            transport_instance = transport_class()

            if transport_instance.is_valid():
                transports.append(transport_instance)
        except (ImportError, AttributeError) as e:
            msg = 'Could not import "{}". (CARRIER_TRANSPORT_CLASSES setting). {}: {}.'.format(
                transport_class_string, e.__class__.__name__, e)
            raise ImportError(msg)

    return transports
