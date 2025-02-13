from django.urls import include, path
from . import models, views


urlpatterns = [
    path("fil_actualite/", views.fil_actualite_view,  name="fil_actualite"),
]