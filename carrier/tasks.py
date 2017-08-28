from celery import shared_task
from django.core.management import call_command


@shared_task
def send_messages():
    call_command('send_messages')
