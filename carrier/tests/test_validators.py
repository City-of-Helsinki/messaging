from django.db import models
from rest_framework import serializers

from carrier.validators import OrValidator


class DummyModel(models.Model):
    field1 = models.CharField(max_length=100, null=True)
    field2 = models.CharField(max_length=100, null=True)


class DummySerializer(serializers.ModelSerializer):
    class Meta:
        model = DummyModel
        fields = '__all__'
        validators = [OrValidator(fields=['field1', 'field2'])]


def test_or_validator_all_empty():
    serializer = DummySerializer(data={})

    assert not serializer.is_valid()
    assert serializer.errors == {
        'non_field_errors': ['At least one of the fields "field1, field2" must have value.']
    }


def test_or_validator_one_value():
    serializer = DummySerializer(data={
        'field1': 'value',
    })

    assert serializer.is_valid()
    assert serializer.validated_data == {
        'field1': 'value',
    }


def test_or_validator_all_values():
    serializer = DummySerializer(data={
        'field1': 'value',
        'field2': 'second value',
    })

    assert serializer.is_valid()
    assert serializer.validated_data == {
        'field1': 'value',
        'field2': 'second value',
    }


def test_or_validator_instance_no_value():
    instance = DummyModel()
    serializer = DummySerializer(instance, data={})

    assert not serializer.is_valid()
    assert serializer.errors == {
        'non_field_errors': ['At least one of the fields "field1, field2" must have value.']
    }


def test_or_validator_existing_value():
    instance = DummyModel(field1='existing value')
    serializer = DummySerializer(instance, data={})

    assert serializer.is_valid()


def test_or_validator_existing_values():
    instance = DummyModel(field1='existing value', field2='second existing value')
    serializer = DummySerializer(instance, data={})

    assert serializer.is_valid()


def test_or_validator_update_value():
    instance = DummyModel(field1='existing value')
    serializer = DummySerializer(instance, data={
        'field1': 'update value',
    })

    assert serializer.is_valid()
    assert serializer.validated_data == {
        'field1': 'update value',
    }


def test_or_validator_new_value():
    instance = DummyModel()
    serializer = DummySerializer(instance, data={
        'field1': 'new value',
    })

    assert serializer.is_valid()
    assert serializer.validated_data == {
        'field1': 'new value',
    }
