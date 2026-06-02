from django.contrib import admin
from .models import Post, PostMedia, Poll, PollOption, PollVote, Comment, Like

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'post_type', 'created_at', 'is_active']
    list_filter = ['post_type', 'created_at', 'is_active']
    search_fields = ['content', 'author__employee_first_name']

class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 1

@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ['question', 'created_at', 'is_multiple_choice', 'duration', 'end_date']
    search_fields = ['question']
    list_filter = ['created_at', 'is_multiple_choice']
    inlines = [PollOptionInline]

@admin.register(PollVote)
class PollVoteAdmin(admin.ModelAdmin):
    list_display = ['poll_option', 'voter', 'created_at']
    search_fields = ['poll_option__option_text', 'voter__employee_first_name']
    list_filter = ['created_at']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'content', 'created_at', 'is_active']
    search_fields = ['content', 'author__employee_first_name', 'post__content']
    list_filter = ['created_at', 'is_active']

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    search_fields = ['user__employee_first_name', 'post__content']
    list_filter = ['created_at']