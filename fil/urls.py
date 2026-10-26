from django.urls import include, path
from . import models, views


urlpatterns = [
    path("fil_actualite/", views.fil_actualite_view,  name="fil_actualite"),
    path("create-poll/", views.create_poll, name="create-poll"),
    path("create-post/", views.create_post, name="create-post"),
    path("vote-poll/", views.vote_poll, name="vote-poll"),
    path("toggle-like/", views.toggle_like, name="toggle_like"),
    path("toggle-comment-like/", views.toggle_comment_like, name="toggle_comment_like"),
    path("get-likers/", views.get_likers, name="get_likers"),
    path("add-comment/", views.add_comment, name="add_comment"),
    path("edit-comment/", views.edit_comment, name="edit_comment"),
    path("delete-comment/", views.delete_comment, name="delete_comment"),
    path("update-post/<int:post_id>/", views.update_post, name="update_post"),
    path("delete-post/<int:post_id>/", views.delete_post, name="delete_post"),
    path("toggle-pin/<int:post_id>/", views.toggle_pin, name="toggle_pin"),
]