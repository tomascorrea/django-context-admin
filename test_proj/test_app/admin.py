from context_admin.models import ContextModelAdmin, InnerContextModelAdmin
from django.contrib import admin
from test_app.models import TestModel, TestSubModel


class TestSubModelInnerModelAdmin(InnerContextModelAdmin):
    model = TestSubModel


class TestModelAdmin(ContextModelAdmin):
    models = [TestSubModelInnerModelAdmin]


admin.site.register(TestModel, TestModelAdmin)
