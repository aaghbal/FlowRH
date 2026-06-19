from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
import json
from django.db import transaction

from horilla.decorators import (
    delete_permission,
    duplicate_permission,
    hx_request_required,
    login_required,
    manager_can_enter,
    permission_required,
)

from .models import Post, Poll, PollOption, PollVote, Like, Comment
from .forms import PollForm
from django.views.decorators.http import require_http_methods

# Create your views here.

@login_required
def fil_actualite_view(request):
    # Get all posts initially
    posts = Post.objects.filter(is_active=True).select_related('author').prefetch_related('media_files', 'comments', 'poll', 'poll__options', 'likes')
    
    # Check if user is admin (superuser or has admin permissions)
    is_admin = request.user.is_superuser or request.user.groups.filter(name__icontains='admin').exists()
    
    user = request.user.employee_get
    
    if is_admin:
        # Admin users can see all posts
        user_visible_posts = list(posts)
    else:
        # Filter posts based on user location for regular users
        user_visible_posts = []
        for post in posts:
            if post.is_visible_to_user(request.user):
                user_visible_posts.append(post)
    
    liked_post_ids = set(post.id for post in user_visible_posts if post.likes.filter(user=user).exists())
    
    # Get all comments for filtered posts to determine which ones are liked by the current user
    all_comments = Comment.objects.filter(post__in=user_visible_posts)
    liked_comment_ids = set(c.id for c in all_comments if c.likes.filter(user=user).exists())
    
    # Get all unique sites for the site selection dropdown
    from employee.models import EmployeeWorkInformation
    available_sites = list(EmployeeWorkInformation.objects.exclude(
        location__isnull=True
    ).values_list(
        'location__site_name', flat=True
    ).distinct().order_by('location__site_name'))
    
    return render(request, "fil/fil_actualite.html", {
        "posts": user_visible_posts, 
        "liked_post_ids": liked_post_ids,
        "liked_comment_ids": liked_comment_ids,
        "available_sites": available_sites,
        "is_admin": is_admin
    })

@csrf_exempt
@login_required
def create_poll(request):
    import logging
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        data = request.POST
        files = request.FILES
        title_data = dict(data)
        question = title_data['title'][1] if 'title' in title_data else ''
        title = title_data['title'][0] if 'title' in title_data else ''
        is_multiple_choice = data.get('is_multiple_choice') in ['true', 'True', '1', True]
        duration = data.get('duration')
        options = [v for k, v in data.items() if k.startswith('choice') and v]
        image = files.get('image')
        document = files.get('document')
        
        # Handle site selection
        selected_sites = data.getlist('sites[]') if 'sites[]' in data else data.getlist('sites')
        
        # Validate required fields
        if not question or not title:
            return JsonResponse({'success': False, 'error': 'Title and question are required.'})
        
        if not options or len(options) < 2:
            return JsonResponse({'success': False, 'error': 'At least 2 options are required.'})

        # Validate file types and sizes
        if image:
            if not image.content_type.startswith('image/'):
                return JsonResponse({'success': False, 'error': 'Invalid image file type.'})
            if image.size > 5 * 1024 * 1024:  # 5MB limit
                return JsonResponse({'success': False, 'error': 'Image file size must be less than 5MB.'})

        if document:
            allowed_doc_types = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
            if document.content_type not in allowed_doc_types:
                return JsonResponse({'success': False, 'error': 'Invalid document file type. Allowed types: PDF, DOC, DOCX, TXT'})
            if document.size > 10 * 1024 * 1024:  # 10MB limit
                return JsonResponse({'success': False, 'error': 'Document file size must be less than 10MB.'})

        try:
            post = Post.objects.create(
                author=request.user.employee_get,
                content=title,
                post_type='poll',
                is_active=True,
                image=image if image else None,
                document=document if document else None
            )
            
            # Set sites if selected
            if selected_sites:
                post.set_sites_list(selected_sites)
                post.save()
                
            poll = Poll.objects.create(
                post=post,
                question=question,
                is_multiple_choice=is_multiple_choice,
                duration=duration
            )
            for opt in options:
                PollOption.objects.create(poll=poll, option_text=opt)
            return JsonResponse({'success': True})
        except Exception as e:
            # Log the error for debugging
            logger.error(f'Error creating poll: {str(e)}')
            return JsonResponse({'success': False, 'error': 'An error occurred while creating the poll.'})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@csrf_exempt
@login_required
@require_POST
def create_post(request):
    content = request.POST.get('content', '').strip()
    image = request.FILES.get('image')
    document = request.FILES.get('document')
    
    # Handle site selection
    selected_sites = request.POST.getlist('sites[]') if 'sites[]' in request.POST else request.POST.getlist('sites')

    # Validate content
    if not content and not image and not document:
        return JsonResponse({'success': False, 'error': 'Content, image, or document is required.'})

    # Validate file types and sizes
    if image:
        if not image.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': 'Invalid image file type.'})
        if image.size > 5 * 1024 * 1024:  # 5MB limit
            return JsonResponse({'success': False, 'error': 'Image file size must be less than 5MB.'})

    if document:
        allowed_doc_types = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
        if document.content_type not in allowed_doc_types:
            return JsonResponse({'success': False, 'error': 'Invalid document file type. Allowed types: PDF, DOC, DOCX, TXT'})
        if document.size > 10 * 1024 * 1024:  # 10MB limit
            return JsonResponse({'success': False, 'error': 'Document file size must be less than 10MB.'})

    try:
        post = Post.objects.create(
            author=request.user.employee_get,
            content=content,
            post_type='text',
            is_active=True,
            image=image if image else None,
            document=document if document else None
        )
        
        # Set sites if selected
        if selected_sites:
            post.set_sites_list(selected_sites)
            post.save()
            
        return JsonResponse({'success': True, 'post_id': post.id})
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error creating post: {str(e)}')
        return JsonResponse({'success': False, 'error': 'An error occurred while creating the post.'})

@csrf_exempt
@login_required
@require_POST
def vote_poll(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        poll_id = data.get('poll_id')
        option_ids = data.get('option_ids', [])
        if not poll_id:
            return JsonResponse({'success': False, 'error': 'Invalid data.'})
        if not isinstance(option_ids, list):
            option_ids = [option_ids]
        poll = Poll.objects.get(id=poll_id)
        user = request.user.employee_get
        # Remove previous votes for this poll by this user
        PollVote.objects.filter(poll_option__poll=poll, voter=user).delete()
        # If option_ids is not empty, add new votes
        if option_ids:
            for option_id in option_ids:
                option = PollOption.objects.get(id=option_id, poll=poll)
                PollVote.objects.get_or_create(poll_option=option, voter=user)
        # Prepare updated poll results
        options = []
        for option in poll.options.all():
            options.append({
                'id': option.id,
                'text': option.option_text,
                'votes': option.get_vote_count(),
                'percent': int(option.get_vote_percentage()),
            })
        return JsonResponse({'success': True, 'options': options})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@login_required
@require_POST
def toggle_like(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        post_id = data.get('post_id')
        if not post_id:
            return JsonResponse({'success': False, 'error': 'Invalid data.'})
        post = Post.objects.get(id=post_id)
        user = request.user.employee_get
        like, created = Like.objects.get_or_create(post=post, user=user)
        if not created:
            # Already liked, so unlike
            like.delete()
            liked = False
        else:
            liked = True
        like_count = post.get_likes_count()
        return JsonResponse({'success': True, 'liked': liked, 'like_count': like_count})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@login_required
@require_POST
def add_comment(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        post_id = data.get('post_id')
        parent_comment_id = data.get('parent_comment_id')
        content = data.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Content is required.'})
        
        # Handle replies
        if parent_comment_id:
            parent_comment = Comment.objects.get(id=parent_comment_id)
            post = parent_comment.post
        elif post_id:
            post = Post.objects.get(id=post_id)
            parent_comment = None
        else:
            return JsonResponse({'success': False, 'error': 'Invalid data.'})
        
        comment = Comment.objects.create(
            post=post,
            parent_comment=parent_comment,
            author=request.user.employee_get,
            content=content,
            is_active=True
        )
        
        # Render the new comment HTML
        from django.template.loader import render_to_string
        
        # Get liked comment IDs for the current user
        user = request.user.employee_get
        liked_comment_ids = set(c.id for c in Comment.objects.filter(post=post) if c.likes.filter(user=user).exists())
        
        comment_html = render_to_string('fil/comment.html', {
            'comment': comment,
            'request': request,
            'liked_comment_ids': liked_comment_ids
        })
        return JsonResponse({'success': True, 'comment_html': comment_html})
    except (Post.DoesNotExist, Comment.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Post or comment not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def toggle_comment_like(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        comment_id = data.get('comment_id')
        if not comment_id:
            return JsonResponse({'success': False, 'error': 'Invalid data.'})
        
        comment = Comment.objects.get(id=comment_id)
        user = request.user.employee_get
        
        # Check if user already liked this comment
        like, created = Like.objects.get_or_create(comment=comment, user=user)
        
        if not created:
            # Already liked, so unlike
            like.delete()
            liked = False
        else:
            liked = True
            
        like_count = comment.get_likes_count()
        return JsonResponse({'success': True, 'liked': liked, 'likes_count': like_count})
    except Comment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Comment not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def delete_comment(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        comment_id = data.get('comment_id')
        if not comment_id:
            return JsonResponse({'success': False, 'error': 'Invalid data.'})
        
        comment = Comment.objects.get(id=comment_id)
        
        # Check if user is the author
        if comment.author != request.user.employee_get:
            return JsonResponse({'success': False, 'error': 'Permission denied.'})
        
        comment.delete()
        return JsonResponse({'success': True})
    except Comment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Comment not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def edit_comment(request):
    """Edit an existing comment"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        comment_id = data.get('comment_id')
        new_content = data.get('content', '').strip()
        
        if not comment_id or not new_content:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
            
        comment = Comment.objects.get(id=comment_id, author=request.user.employee_get)
        comment.content = new_content
        comment.save()
        
        return JsonResponse({
            'success': True,
            'comment_id': comment.id,
            'content': comment.content,
            'updated_at': comment.updated_at.strftime('%b. %d, %Y, %I:%M %p'),
            'user_name': comment.author.get_full_name()
        })
        
    except Comment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Comment not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@login_required
@require_http_methods(['POST'])
def update_post(request, post_id):
    """
    Update an existing post
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Starting post update for post_id: {post_id}")
    
    try:
        post = get_object_or_404(Post, id=post_id, author=request.user.employee_get)
        
        # Log incoming request data
        logger.info(f"Request FILES: {dict(request.FILES)}")
        logger.info(f"Request POST: {dict(request.POST)}")
        
        # Handle file uploads and form data
        image = request.FILES.get('image')
        document = request.FILES.get('document')
        content = request.POST.get('content', '').strip()
        remove_image = request.POST.get('remove_image') == 'true'
        remove_document = request.POST.get('remove_document') == 'true'
        
        # Log file information if present
        if document:
            logger.info(f"Document file info - Name: {document.name}, Size: {document.size}, Content-Type: {document.content_type}")
        if image:
            logger.info(f"Image file info - Name: {image.name}, Size: {image.size}, Content-Type: {image.content_type}")
        
        # Validate content
        if not content and not image and not document and not post.image and not post.document:
            return JsonResponse({'success': False, 'error': 'Content, image, or document is required.'})

        # Validate file types and sizes
        if image:
            if not image.content_type.startswith('image/'):
                return JsonResponse({'success': False, 'error': 'Invalid image file type.'})
            if image.size > 5 * 1024 * 1024:  # 5MB limit
                return JsonResponse({'success': False, 'error': 'Image file size must be less than 5MB.'})

        if document:
            allowed_doc_types = [
                'application/pdf', 
                'application/msword', 
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'text/plain'
            ]
            if document.content_type not in allowed_doc_types:
                return JsonResponse({'success': False, 'error': 'Invalid document file type. Allowed types: PDF, DOC, DOCX, XLS, XLSX, TXT'})
            if document.size > 10 * 1024 * 1024:  # 10MB limit
                return JsonResponse({'success': False, 'error': 'Document file size must be less than 10MB.'})

        # Update post content
        if content:
            post.content = content
            logger.info("Updated post content")

        # Handle poll data if this is a poll
        if post.post_type == 'poll':
            try:
                # Get poll instance
                poll_id = request.POST.get('poll_id')
                if not poll_id:
                    return JsonResponse({'success': False, 'error': 'Poll ID is required'})
                
                poll = get_object_or_404(Poll, id=poll_id, post=post)
                
                # Update poll question and settings
                poll.question = request.POST.get('poll_question', poll.question)
                poll.is_multiple_choice = request.POST.get('is_multiple_choice') in ('true', 'on', True)
                
                # Update poll duration and end date if duration is provided
                duration = request.POST.get('poll_duration')
                if duration and duration.isdigit():
                    duration_days = int(duration)
                    poll.duration = duration_days
                    poll.end_date = timezone.now() + timezone.timedelta(days=duration_days)
                elif duration == '':  # Clear duration if empty
                    poll.duration = None
                    poll.end_date = None
                
                poll.save()
                logger.info(f"Updated poll settings: {poll}")
                
                # Get existing options
                existing_options = {str(opt.id): opt for opt in poll.options.all()}
                updated_option_ids = set()
                
                # Debug: Log all POST data
                logger.info("=== DEBUG: All POST data ===")
                for k, v in request.POST.items():
                    logger.info(f"POST['{k}'] = '{v}'")
                
                # Debug: Log existing options
                logger.info("=== DEBUG: Existing poll options ===")
                for opt_id, opt in existing_options.items():
                    logger.info(f"Option ID: {opt_id}, Text: '{opt.option_text}', Votes: {opt.votes}")
                
                # Process updated options
                for key, value in request.POST.items():
                    if key.startswith('poll_option_') and value.strip():
                        option_text = value.strip()
                        option_key = key.replace('poll_option_', '')
                        
                        logger.info(f"\nProcessing option - Key: '{key}', Raw Value: '{value}'")
                        logger.info(f"Option Key: '{option_key}', Option Text: '{option_text}'")
                        
                        # Handle existing options (with numeric IDs)
                        if option_key.isdigit() and option_key in existing_options:
                            option = existing_options[option_key]
                            logger.info(f"Found existing option: ID {option_key}, Current Text: '{option.option_text}'")
                            if option.option_text != option_text:
                                option.option_text = option_text
                                option.save()
                                logger.info(f"Updated poll option {option_key} to: '{option_text}'")
                            else:
                                logger.info(f"Option {option_key} text unchanged")
                            updated_option_ids.add(option_key)
                        # Handle new options (with 'new', 'poll_option_new', or other non-numeric keys)
                        elif option_key in ['new', 'poll_option_new'] or not option_key.isdigit():
                            logger.info("Detected new poll option")
                            try:
                                option = PollOption.objects.create(
                                    poll=poll,
                                    option_text=option_text
                                )
                                # No need to set votes=0 here as it's a many-to-many field
                                # and will be empty by default
                                updated_option_ids.add(str(option.id))
                                logger.info(f"Successfully created new poll option: '{option_text}' with ID {option.id}")
                            except Exception as e:
                                logger.error(f"Error creating poll option: {str(e)}", exc_info=True)
                                logger.error(f"Failed to create option with text: '{option_text}'")
                                continue
                        else:
                            logger.warning(f"Unexpected option key format: {key} = {value}")
                
                # Delete options that were removed if they have no votes
                for option_id, option in existing_options.items():
                    if option_id not in updated_option_ids:
                        if option.votes == 0:  # Only delete if no one has voted
                            logger.info(f"Deleting removed poll option: {option.option_text}")
                            option.delete()
                        else:
                            logger.info(f"Keeping poll option with votes: {option.option_text}")
                
                logger.info("Poll updated successfully")
                
            except Exception as e:
                logger.error(f"Error updating poll: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return JsonResponse({'success': False, 'error': f'Error updating poll: {str(e)}'})

        # Update post image
        if image:
            logger.info("Processing image upload")
            post.image = image
            logger.info("Image updated successfully")
        elif remove_image:
            logger.info("Removing image as requested")
            post.image = None

        # Update post document
        if document:
            logger.info(f"Processing document upload - Type: {document.content_type}")
            try:
                post.document = document
                logger.info("Document updated successfully")
            except Exception as e:
                logger.error(f"Error updating document: {str(e)}")
                return JsonResponse({'success': False, 'error': f'Error processing document: {str(e)}'})
        elif remove_document:
            logger.info("Removing document as requested")
            post.document = None

        try:
            post.save()
            logger.info("Post saved successfully")
        except Exception as e:
            logger.error(f"Error saving post: {str(e)}")
            return JsonResponse({'success': False, 'error': f'Error saving post: {str(e)}'})

        response_data = {
            'success': True,
            'post_id': post.id,
            'content': post.content,
            'updated_at': post.updated_at.strftime('%b. %d, %Y, %I:%M %p'),
            'user_name': post.author.get_full_name()
        }
        if post.document:
            response_data['document_url'] = post.document.url
            response_data['document_name'] = post.document.name.split('/')[-1]
        logger.info(f"Returning success response: {response_data}")
        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

from django.utils import timezone
from datetime import timedelta

def format_time_ago(datetime_obj):
    """Format datetime as 'time ago' string"""
    if not datetime_obj:
        return "Unknown"
    
    now = timezone.now()
    diff = now - datetime_obj
    
    if diff < timedelta(minutes=1):
        return "Just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff < timedelta(days=7):
        days = diff.days
        return f"{days} day{'s' if days > 1 else ''} ago"
    elif diff < timedelta(days=30):
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff < timedelta(days=365):
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"

import logging
logger = logging.getLogger(__name__)

@login_required
@require_http_methods(['POST'])
def delete_post(request, post_id):
    """
    Delete a post (soft delete by setting is_active=False)
    Only the post author can delete their post
    """
    try:
        logger.info(f"Attempting to delete post {post_id} for user {request.user.id}")
        
        # Get the post or return 404 if not found
        try:
            post = Post.objects.get(id=post_id, is_active=True)
        except Post.DoesNotExist:
            logger.warning(f"Post {post_id} not found or already deleted")
            return JsonResponse({'error': 'Post not found or already deleted'}, status=404)
        
        # Check if the current user is the author of the post
        if post.author.employee_user_id != request.user:
            logger.warning(f"User {request.user.id} attempted to delete post {post_id} without permission")
            return JsonResponse(
                {'error': 'You do not have permission to delete this post'}, 
                status=403
            )
        
        # Log post details before deletion for debugging
        logger.info(f"Deleting post {post_id} with author {post.author.id}")
        
        # Perform soft delete
        post.is_active = False
        post.save()
        
        logger.info(f"Successfully soft-deleted post {post_id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Post supprimée avec succès',
            'post_id': post_id
        })
        
    except Exception as e:
        logger.error(f"Error deleting post {post_id}: {str(e)}", exc_info=True)
        return JsonResponse(
            {'error': f'Une erreur est survenue lors de la suppression du post: {str(e)}'}, 
            status=500
        )

@login_required
def get_likers(request):
    """Get the list of users who liked a post or comment"""
    try:
        post_id = request.GET.get('post_id')
        comment_id = request.GET.get('comment_id')
        
        if post_id:
            post = Post.objects.get(id=post_id)
            likes = Like.objects.filter(post=post).select_related('user')
            likers = []
            for like in likes:
                profile_image = None
                if like.user.employee_profile:
                    profile_image = like.user.employee_profile.url
                
                # Get job position
                job_position = None
                if hasattr(like.user, 'employee_work_info') and like.user.employee_work_info:
                    if hasattr(like.user.employee_work_info, 'job_position_id') and like.user.employee_work_info.job_position_id:
                        job_position = str(like.user.employee_work_info.job_position_id)
                
                likers.append({
                    'id': like.user.id,
                    'name': f"{like.user.employee_first_name} {like.user.employee_last_name}",
                    'profile_image': profile_image,
                    'job_position': job_position or 'Employee',
                    'created_at': format_time_ago(like.created_at)
                })
            
        elif comment_id:
            comment = Comment.objects.get(id=comment_id)
            likes = Like.objects.filter(comment=comment).select_related('user')
            likers = []
            for like in likes:
                profile_image = None
                if like.user.employee_profile:
                    profile_image = like.user.employee_profile.url
                
                # Get job position
                job_position = None
                if hasattr(like.user, 'employee_work_info') and like.user.employee_work_info:
                    if hasattr(like.user.employee_work_info, 'job_position_id') and like.user.employee_work_info.job_position_id:
                        job_position = str(like.user.employee_work_info.job_position_id)
                
                likers.append({
                    'id': like.user.id,
                    'name': f"{like.user.employee_first_name} {like.user.employee_last_name}",
                    'profile_image': profile_image,
                    'job_position': job_position or 'Employee',
                    'created_at': format_time_ago(like.created_at)
                })
        else:
            return JsonResponse({'success': False, 'error': 'Invalid request.'})
        
        return JsonResponse({'success': True, 'likers': likers})
        
    except (Post.DoesNotExist, Comment.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Post or comment not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})