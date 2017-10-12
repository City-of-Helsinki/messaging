import uuid
from collections import defaultdict

import requests
from django.conf import settings
from django.conf.global_settings import LANGUAGES
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from enumfields import EnumField

from .enums import MessageStatus, RecipientStatus, TransportType


class Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)
    pushbullet_access_token = models.CharField(max_length=100, null=True, blank=True)
    firebase_token = models.CharField(max_length=255, null=True, blank=True)
    language = models.CharField(max_length=7, choices=LANGUAGES, null=True, blank=True)
    preferred_transport = EnumField(TransportType, max_length=100, null=True, blank=True)


class MessageSendResult:
    def __init__(self, errors=None, warnings=None, sent=None):
        self.errors = errors
        self.warning = warnings
        self.sent = sent

    def has_errors(self):
        return bool(self.errors)


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_name = models.CharField(max_length=255, null=True, blank=True)
    from_email = models.CharField(max_length=255, null=True, blank=True)
    send_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(editable=False, null=True, blank=True)
    created_at = models.DateTimeField(editable=False, blank=True, auto_now_add=True)
    status = EnumField(MessageStatus, max_length=255, default=MessageStatus.PENDING_INFO)

    def validate(self):
        errors = []
        if self.status != MessageStatus.READY_TO_SEND:
            errors.append('Status is not "{}", but "{}".'.format(MessageStatus.READY_TO_SEND, self.status))

        if self.contents.count() == 0:
            errors.append('No content.')

        if self.recipients.filter(status=RecipientStatus.READY_TO_SEND).count() == 0:
            errors.append('No recipients ready.')

        return False if errors else True, errors

    def is_sendable(self):
        return self.validate()[0]

    def get_validation_errors(self):
        return self.validate()[1]

    def get_content_languages(self):
        return set(self.contents.all().values_list('language', flat=True))

    def get_content_in_language(self, language):
        available_languages = self.get_content_languages()

        if language not in available_languages:
            # Sort available content languages by CARRIER_CONTENT_LANGUAGES and take the first available
            ordered_languages = list(available_languages)
            ordered_languages.sort(key=lambda x: settings.CARRIER_CONTENT_LANGUAGES.index(x) if
                                   x in settings.CARRIER_CONTENT_LANGUAGES else 9999)
            language = ordered_languages[0]

        content = self.contents.filter(language=language).first()

        return content

    def fetch_contact_info_for_recipients(self):
        # Gather the uuids of the contacts we need to fetch info for
        recipient_uuids = [
            str(v) for v in self.recipients.filter(uuid__isnull=False, contact__isnull=True).values_list(
                'uuid', flat=True)]

        if not recipient_uuids:
            return

        url = '{}?ids={}'.format(settings.CONTACT_INFO_URL, ','.join(recipient_uuids))

        r = requests.get(url, auth=(settings.TUNNISTAMO_USERNAME, settings.TUNNISTAMO_PASSWORD))
        r.raise_for_status()

        for contact_id, contact_info in r.json().items():
            if not contact_info.get('contact_method'):
                continue

            Contact.objects.update_or_create(
                id=contact_id,
                email=contact_info.get('email'),
                pushbullet_access_token=contact_info.get('pushbullet'),
                firebase_token=contact_info.get('firebase'),
                phone=contact_info.get('phone'),
                language=contact_info.get('language'),
                preferred_transport=contact_info.get('contact_method')
            )
            # self.recipients.filter(uuid=contact_id).update(contact=contact)

    def attach_contacts_to_recipients(self):
        for recipient in self.recipients.filter(status=RecipientStatus.PENDING_INFO):
            recipient.attach_contact()

    def validate_recipients(self, transports):
        for recipient in self.recipients.filter():
            # Check that at least one transport can send to the recipient
            for transport in transports:
                if transport.is_suitable_for_recipient(recipient):
                    recipient.status = RecipientStatus.READY_TO_SEND
                    break
            else:
                recipient.status = RecipientStatus.IGNORED

            recipient.save()

        self.status = MessageStatus.READY_TO_SEND
        self.save()

    def send(self, transports):
        if not self.is_sendable():
            return MessageSendResult(errors=self.get_validation_errors(), sent=False)

        self.status = MessageStatus.SENDING
        self.save()

        errors = []
        warnings = []
        transport_recipients = defaultdict(list)
        for recipient in self.recipients.filter(status=RecipientStatus.READY_TO_SEND):
            for transport in transports:
                # Use the first suitable transport
                if transport.is_suitable_for_recipient(recipient):
                    transport_recipients[transport].append(recipient)
                    break
            else:
                warnings.append('No suitable transport found for recipient id {}. Skipping.'.format(recipient.id))

        for transport, recipients in transport_recipients.items():
            result = transport.send(self, recipients)
            errors.extend(result['errors'])

        self.sent_at = timezone.now()

        if not errors:
            self.status = MessageStatus.SENT
        else:
            self.status = MessageStatus.ERROR

        self.save()

        return MessageSendResult(errors=errors, warnings=warnings, sent=True)


class Recipient(models.Model):
    message = models.ForeignKey(Message, related_name="recipients", on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.SET_NULL)
    uuid = models.UUIDField(null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)
    language = models.CharField(max_length=7, choices=LANGUAGES, null=True, blank=True)
    transport = EnumField(TransportType, max_length=100, null=True, blank=True)
    status = EnumField(RecipientStatus, max_length=255, default=RecipientStatus.PENDING_INFO)

    def get_email(self):
        if self.email:
            return self.email

        if self.contact and self.contact.email:
            return self.contact.email

        return None

    def get_phone(self):
        if self.phone:
            return self.phone

        if self.contact and self.contact.phone:
            return self.contact.phone

        return None

    def get_pushbullet_access_token(self):
        if self.contact and self.contact.pushbullet_access_token:
            return self.contact.pushbullet_access_token

        return None

    def get_firebase_token(self):
        if self.contact and self.contact.firebase_token:
            return self.contact.firebase_token

        return None

    def get_language(self):
        if self.language:
            return self.language

        if self.contact and self.contact.language:
            return self.contact.language

        if getattr(settings, 'CARRIER_CONTENT_LANGUAGES', None):
            return settings.CARRIER_CONTENT_LANGUAGES[0]

        return None

    def attach_contact(self):
        if not self.uuid or self.contact:
            return

        try:
            self.contact = Contact.objects.get(pk=self.uuid)
        except Contact.DoesNotExist:
            pass

        self.save()


class Content(models.Model):
    message = models.ForeignKey(Message, related_name="contents", on_delete=models.CASCADE)
    language = models.CharField(max_length=7, choices=LANGUAGES, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    html = models.TextField(null=True, blank=True)
    short_text = models.CharField(max_length=255, null=True, blank=True)


@receiver(post_save, sender=Recipient)
def check_for_contact(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.uuid:
        try:
            contact = Contact.objects.get(pk=instance.uuid)
            instance.contact = contact
            instance.save()
        except Contact.DoesNotExist:
            pass
