from django.utils import unittest
from utils import create_model, install
from django.db import models

class ListTestCase(unittest.TestCase):

    def setUp(self):
        admin_opts = {}
        fields = {'name': models.CharField(max_length=255)}
        self.dynamic_model = create_model('DynamicModel', fields=fields, app_label='context_admin', admin_opts={})

        fields = {  'name': models.CharField(max_length=255),
                    'dynamic_model': models.ForeignKey(self.dynamic_model)
                    }

        self.dynamic_inner_model = create_model('DynamicInnerModel', fields=fields, app_label='context_admin', admin_opts={})
        

        install(self.dynamic_model)
        install(self.dynamic_inner_model)

        instance = self.dynamic_model()
        instance.save()

    def test_admin_edit_page_list_inner_models(self):
        pass

