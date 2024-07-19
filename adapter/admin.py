from django.contrib import admin


from .models import *

models = [
    JasminGroup
]

admin.site.register(models)
