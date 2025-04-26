from django.contrib import admin


from .models import *

models = [
    JasminGroup,
    JasminUser
]

admin.site.register(models)
