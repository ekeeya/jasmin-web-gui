from django.contrib import admin


from .models import *

models = [
    User,
    WorkSpace,
    WorkSpaceMembership
]

admin.site.register(models)
