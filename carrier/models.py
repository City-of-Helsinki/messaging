import uuid

from django.conf.global_settings import LANGUAGES
from django.db import models
from enumfields import EnumField

from .enums import MessageStatus, RecipientStatus


class Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.CharField(max_length=100, null=True, blank=True)
    language = models.CharField(max_length=7, choices=LANGUAGES, null=True, blank=True)
    preferred_transport = models.CharField(max_length=100, null=True, blank=True)


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_name = models.CharField(max_length=255, null=True, blank=True)
    from_email = models.CharField(max_length=255, null=True, blank=True)
    send_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(editable=False, null=True, blank=True)
    created_at = models.DateTimeField(editable=False, blank=True, auto_now_add=True)
    status = EnumField(MessageStatus, max_length=255, default=MessageStatus.PENDING)


class Recipient(models.Model):
    message = models.ForeignKey(Message, related_name="recipients", on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, null=True, blank=True, on_delete=models.PROTECT)
    email = models.CharField(max_length=100, null=True, blank=True)
    language = models.CharField(max_length=7, choices=LANGUAGES, null=True, blank=True)
    transport = models.CharField(max_length=100, null=True, blank=True)
    status = EnumField(RecipientStatus, max_length=255, default=RecipientStatus.PENDING)


class Content(models.Model):
    message = models.ForeignKey(Message, related_name="contents", on_delete=models.CASCADE)
    language = models.CharField(max_length=7, choices=LANGUAGES, null=True, blank=True)
    subject = models.CharField(max_length=255, null=True, blank=True)
    text = models.TextField(null=True, blank=True)
    html = models.TextField(null=True, blank=True)
    short_text = models.CharField(max_length=255, null=True, blank=True)
