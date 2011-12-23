from django.db import models

# Create your models here.


class TestModel(models.Model):
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name



class TestSubModel(models.Model):
    test_model = models.ForeignKey(TestModel)
    name = models.CharField(max_length=200)


    def __unicode__(self):
        return self.name

