from rest_framework import mixins, routers
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from carrier.serializers import MessageSerializer

from .models import Message

all_views = []


def register_view(klass, name, base_name=None):
    entry = {
        'class': klass,
        'name': name
    }
    if base_name is not None:
        entry['base_name'] = base_name
    all_views.append(entry)


class APIRouter(routers.DefaultRouter):
    def __init__(self):
        super().__init__()
        self.registered_api_views = set()
        self._register_all_views()

    def _register_view(self, view):
        if view['class'] in self.registered_api_views:
            return
        self.registered_api_views.add(view['class'])
        self.register(view['name'], view['class'], base_name=view.get("base_name"))

    def _register_all_views(self):
        for view in all_views:
            self._register_view(view)


class MessageViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

    def perform_create(self, serializer):
        from .tasks import send_message

        serializer.save()

        send_message.delay(serializer.instance.id)


register_view(MessageViewSet, 'message')
