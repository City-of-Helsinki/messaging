from enumfields.drf import EnumSupportSerializerMixin
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from carrier.models import Content, Message, Recipient


class CreateRelatedMixin:
    def create(self, validated_data):
        assert hasattr(self, 'Meta'), (
            'Class {serializer_class} missing "Meta" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        assert hasattr(self.Meta, 'create_related_fields'), (
            'Class {serializer_class} missing "Meta.create_related_fields" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )

        related_validated_data = {}
        for field_name in self.Meta.create_related_fields:
            related_validated_data[field_name] = validated_data.pop(field_name, [])

        instance = super().create(validated_data)

        for field_name in self.Meta.create_related_fields:
            if field_name not in related_validated_data:
                continue

            child_model = self.fields[field_name].child.Meta.model
            child_serializer_class = self.fields[field_name].child.__class__
            child_manager = getattr(instance, field_name)

            foreign_field_name = None
            for child_field in child_model._meta.get_fields():
                if child_field.remote_field and child_field.remote_field.model == self.__class__.Meta.model:
                    foreign_field_name = child_field.name
                    break

            assert foreign_field_name, 'Foreign field for class {} not found from class {}'.format(
                self.__class__, child_model)

            for item in related_validated_data[field_name]:
                serializer = child_serializer_class(data=item)

                try:
                    serializer.is_valid(raise_exception=True)
                except ValidationError as e:
                    raise ValidationError({
                        field_name: e.detail
                    })

                item_instance = serializer.save(**{
                    foreign_field_name: instance
                })

                child_manager.add(item_instance)

        return instance


class RecipientSerializer(EnumSupportSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = Recipient
        fields = '__all__'
        read_only_fields = ('message', 'transport', 'status')


class ContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = '__all__'
        read_only_fields = ('message', )


class MessageSerializer(CreateRelatedMixin, EnumSupportSerializerMixin, serializers.ModelSerializer):
    recipients = RecipientSerializer(many=True)
    contents = ContentSerializer(many=True)

    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ('created_at', 'sent_at', 'status')
        create_related_fields = ('recipients', 'contents')
