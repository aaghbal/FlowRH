from django.db import models
from django.utils.translation import gettext_lazy as _
from employee.models import Employee
from django.core.validators import FileExtensionValidator

class Post(models.Model):
    """
    Post model for fil d'actualité
    """
    POST_TYPE_CHOICES = [
        ('text', _('Text')),
        ('poll', _('Poll')), 
    ]
    
    author = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='posts',
        verbose_name=_("Author")
    )
    content = models.TextField(
        max_length=5000, 
        verbose_name=_("Content")
    )
    post_type = models.CharField(
        max_length=10, 
        choices=POST_TYPE_CHOICES, 
        default='text',
        verbose_name=_("Post Type")
    )
    sites = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Sites"),
        help_text=_("Comma-separated list of sites where this post should be displayed")
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(
        upload_to='fil/images/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Image')
    )
    document = models.FileField(
        upload_to='fil/documents/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name=_('Document'),
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx'])]
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Post")
        verbose_name_plural = _("Posts")
    
    def __str__(self):
        return f"{self.author.get_full_name()} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"
    
    def get_likes_count(self):
        return self.likes.count()
    
    def get_comments_count(self):
        return self.comments.count()
    
    def get_sites_list(self):
        """Return a list of sites from the comma-separated string"""
        if self.sites:
            return [site.strip() for site in self.sites.split(',') if site.strip()]
        return []
    
    def set_sites_list(self, sites_list):
        """Set the sites from a list of site names"""
        if sites_list:
            self.sites = ', '.join(sites_list)
        else:
            self.sites = None
    
    def is_visible_to_user(self, user):
        """Check if this post should be visible to a specific user based on their location"""
        # Admin users can see all posts
        if user.is_superuser or user.groups.filter(name__icontains='admin').exists():
            return True
            
        if not self.sites:
            # If no specific sites are set, the post is visible to all
            return True
        
        try:
            # Get the user's work location
            if hasattr(user, 'employee_get') and hasattr(user.employee_get, 'employee_work_info'):
                user_location = user.employee_get.employee_work_info.location
                if user_location and user_location.site_name in self.get_sites_list():
                    return True
            return False
        except:
            # If there's any error getting user location, show the post
            return True


class PostMedia(models.Model):
    """
    Model for post attachments (photos, documents)
    """
    MEDIA_TYPE_CHOICES = [
        ('photo', _('Photo')),
        ('document', _('Document')),
    ]
    
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='media_files'
    )
    media_type = models.CharField(
        max_length=10, 
        choices=MEDIA_TYPE_CHOICES,
        verbose_name=_("Media Type")
    )
    file = models.FileField(
        upload_to='fil/media/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx']
            )
        ],
        verbose_name=_("File")
    )
    file_name = models.CharField(max_length=255, verbose_name=_("File Name"))
    file_size = models.PositiveIntegerField(verbose_name=_("File Size (bytes)"))
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Post Media")
        verbose_name_plural = _("Post Media")
    
    def __str__(self):
        return f"{self.post.author.get_full_name()} - {self.file_name}"


class Poll(models.Model):
    """
    Poll model for voting posts
    """
    post = models.OneToOneField(
        Post, 
        on_delete=models.CASCADE, 
        related_name='poll'
    )
    question = models.TextField(
        max_length=1000,
        verbose_name=_('Poll Question')
    )
    is_multiple_choice = models.BooleanField(
        default=False,
        verbose_name=_('Allow Multiple Choices')
    )
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Duration (days)')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name=_('End Date')
    )

    class Meta:
        verbose_name = _('Poll')
        verbose_name_plural = _('Polls')

    def __str__(self):
        return f"Poll: {self.question[:50]}..."

    def get_total_votes(self):
        return PollVote.objects.filter(poll_option__poll=self).count()


class PollOption(models.Model):
    """
    Poll options for voting
    """
    poll = models.ForeignKey(
        Poll, 
        on_delete=models.CASCADE, 
        related_name='options'
    )
    option_text = models.CharField(
        max_length=200,
        verbose_name=_("Option Text")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Poll Option")
        verbose_name_plural = _("Poll Options")
        unique_together = ['poll', 'option_text']
    
    def __str__(self):
        return self.option_text
    
    def get_vote_count(self):
        return self.votes.count()
    
    def get_vote_percentage(self):
        total_votes = self.poll.get_total_votes()
        if total_votes == 0:
            return 0
        return (self.get_vote_count() / total_votes) * 100


class PollVote(models.Model):
    """
    Individual votes on poll options
    """
    poll_option = models.ForeignKey(
        PollOption, 
        on_delete=models.CASCADE, 
        related_name='votes'
    )
    voter = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='poll_votes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Poll Vote")
        verbose_name_plural = _("Poll Votes")
        unique_together = ['poll_option', 'voter']  # One vote per option per user
    
    def __str__(self):
        return f"{self.voter.get_full_name()} voted for {self.poll_option.option_text}"


class Comment(models.Model):
    """
    Comments on posts
    """
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    author = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='comments'
    )
    parent_comment = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies',
        verbose_name=_("Parent Comment")
    )
    content = models.TextField(
        max_length=1000,
        verbose_name=_("Comment Content")
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")
    
    def __str__(self):
        return f"{self.author.get_full_name()}: {self.content[:50]}..."
    
    def get_likes_count(self):
        return self.likes.count()
    
    def is_liked_by_user(self, user):
        """Check if the comment is liked by a specific user"""
        return self.likes.filter(user=user).exists()


class Like(models.Model):
    """
    Likes for posts and comments
    """
    user = models.ForeignKey(
        Employee, 
        on_delete=models.CASCADE, 
        related_name='likes'
    )
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='likes'
    )
    comment = models.ForeignKey(
        Comment, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Like")
        verbose_name_plural = _("Likes")
        constraints = [
            models.CheckConstraint(
                check=models.Q(post__isnull=False) | models.Q(comment__isnull=False),
                name='like_post_or_comment'
            ),
            # Unconditional for the same reason as Employee.unique_badge_id:
            # MariaDB skips conditional unique constraints, and NULLs count as
            # distinct in a unique index, so the null rows stay exempt anyway.
            models.UniqueConstraint(
                fields=['user', 'post'],
                name='unique_post_like'
            ),
            models.UniqueConstraint(
                fields=['user', 'comment'],
                name='unique_comment_like'
            )
        ]
    
    def __str__(self):
        if self.post:
            return f"{self.user.get_full_name()} likes post by {self.post.author.get_full_name()}"
        elif self.comment:
            return f"{self.user.get_full_name()} likes comment by {self.comment.author.get_full_name()}"


class FilSettings(models.Model):
    """
    Settings for fil d'actualité
    """
    company = models.OneToOneField(
        'base.Company',  # Assuming you have a Company model
        on_delete=models.CASCADE,
        related_name='fil_settings',
        null=True,
        blank=True
    )
    allow_anonymous_posts = models.BooleanField(
        default=False,
        verbose_name=_("Allow Anonymous Posts")
    )
    max_post_length = models.PositiveIntegerField(
        default=5000,
        verbose_name=_("Maximum Post Length")
    )
    allow_file_uploads = models.BooleanField(
        default=True,
        verbose_name=_("Allow File Uploads")
    )
    max_file_size_mb = models.PositiveIntegerField(
        default=10,
        verbose_name=_("Maximum File Size (MB)")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Fil Settings")
        verbose_name_plural = _("Fil Settings")