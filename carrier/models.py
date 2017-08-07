import uuid

from django.conf.global_settings import LANGUAGES
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from enumfields import EnumField

from messaging import settings

from .enums import MessageStatus, RecipientStatus, TransportType


class Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=100, null=True, blank=True)
    language = models.CharField(max_length=7, choices=LANGUAGES, null=True, blank=True)
    preferred_transport = EnumField(TransportType, max_length=100, null=True, blank=True)


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_name = models.CharField(max_length=255, null=True, blank=True)
    from_email = models.CharField(max_length=255, null=True, blank=True)
    send_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(editable=False, null=True, blank=True)
    created_at = models.DateTimeField(editable=False, blank=True, auto_now_add=True)
    status = EnumField(MessageStatus, max_length=255, default=MessageStatus.PENDING_INFO)

    def is_sendable(self):
        errors = []
        if self.status != MessageStatus.READY_TO_SEND:
            errors.append('Status is not "{}", but "{}".'.format(MessageStatus.READY_TO_SEND, self.status))

        if self.contents.count() == 0:
            errors.append('No content.')

        if self.recipients.filter(status=RecipientStatus.READY_TO_SEND).count() == 0:
            errors.append('No recipients ready.')

        return False if errors else True, errors

    def get_content_languages(self):
        languages = []
        for content in self.contents.all():
            languages.append(content.language if content.language else settings.CARRIER_CONTENT_LANGUAGES[0])

        return languages

    def get_content_in_language(self, language):
        available_languages = self.get_content_languages()

        if language not in available_languages:
            # Sort available content languages by CARRIER_CONTENT_LANGUAGES
            ordered_languages = [x for (y, x) in sorted(zip(settings.CARRIER_CONTENT_LANGUAGES, available_languages))]
            language = ordered_languages[0]

        content = self.contents.filter(language=language).first()

        return content


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

    def get_language(self):
        if self.language:
            return self.language

        if self.contact and self.contact.language:
            return self.contact.language

        if getattr(settings, 'CARRIER_CONTENT_LANGUAGES', None):
            return settings.CARRIER_CONTENT_LANGUAGES[0]

        return None


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
