import factory
from pytest_factoryboy import register

from carrier.models import Contact, Content, Message, Recipient


@register
class ContactFactory(factory.DjangoModelFactory):
    class Meta:
        model = Contact


@register
class ContentFactory(factory.DjangoModelFactory):
    class Meta:
        model = Content


@register
class MessageFactory(factory.DjangoModelFactory):
    class Meta:
        model = Message


@register
class RecipientFactory(factory.DjangoModelFactory):
    class Meta:
        model = Recipient
