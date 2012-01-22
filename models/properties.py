from google.appengine.ext import db
from google.appengine.api import datastore_types
from django.utils import simplejson

class JsonProperty(db.TextProperty):
    def get_value_for_datastore(self, model_instance):
        value = super(JsonProperty, self).get_value_for_datastore(model_instance)
        return self._deflate(self.convert_field_to_property(value))

    def convert_field_to_property(self, field):
        return field

    def validate(self, value):
        if value is not None and not isinstance(value, (dict, list, tuple)):
            raise db.BadValueError('Property %s must be a dict, list or '
                                   'tuple.' % self.name)

        return value

    def make_value_from_datastore(self, value):
        return self.convert_property_to_field(self._inflate(value))

    def convert_property_to_field(self, value):
        return value

    def _inflate(self, value):
        if value is None:
            return {}
        if isinstance(value, unicode) or isinstance(value, str):
            return simplejson.loads(value)
        return value

    def _deflate(self, value):
        return simplejson.dumps(value)

    data_type = datastore_types.Text
