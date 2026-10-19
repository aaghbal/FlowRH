"""
decorators.py

Custom decorators for permission and manager checks in the application.
"""

from functools import wraps

from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render

from recruitment.department_heads import DEPARTMENT_HEAD_PERMS, is_department_head
from recruitment.models import Recruitment, Stage


def decorator_with_arguments(decorator):
    """
    Decorator that allows decorators to accept arguments and keyword arguments.

    Args:
        decorator (function): The decorator function to be wrapped.

    Returns:
        function: The wrapper function.

    """

    def wrapper(*args, **kwargs):
        """
        Wrapper function that captures the arguments and keyword arguments.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            function: The inner wrapper function.

        """

        def inner_wrapper(func):
            """
            Inner wrapper function that applies the decorator to the function.

            Args:
                func (function): The function to be decorated.

            Returns:
                function: The decorated function.

            """
            return decorator(func, *args, **kwargs)

        return inner_wrapper

    return wrapper


@decorator_with_arguments
def manager_can_enter(function, perm):
    """
    Decorator that checks if the user has the specified permission or is a manager.

    Args:
        perm (str): The permission to check.

    Returns:
        function: The decorated function.

    Raises:
        None

    """

    def _function(request, *args, **kwargs):
        """
        Inner function that performs the permission and manager check.

        Args:
            request (HttpRequest): The request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponse: The response from the decorated function.

        """
        user = request.user
        # employee_get, not the company filtered Employee.objects: a None
        # employee would match every stage/recruitment without manager
        employee = getattr(user, "employee_get", None)
        is_manager = employee is not None and (
            Stage.objects.filter(stage_managers=employee).exists()
            or Recruitment.objects.filter(recruitment_managers=employee).exists()
        )
        if user.has_perm(perm) or is_manager:
            return function(request, *args, **kwargs)
        # Department heads only get in for consultation (view permissions)
        if perm in DEPARTMENT_HEAD_PERMS and is_department_head(user):
            return function(request, *args, **kwargs)
        messages.info(request, "You dont have permission.")
        previous_url = request.META.get("HTTP_REFERER", "/")
        script = f'<script>window.location.href = "{previous_url}"</script>'
        key = "HTTP_HX_REQUEST"
        if key in request.META.keys():
            return render(request, "decorator_404.html")
        return HttpResponse(script)

    return _function


@decorator_with_arguments
def recruitment_manager_can_enter(function, perm):
    """
    Decorator that checks if the user has the specified permission or is a recruitment manager.

    Args:
        perm (str): The permission to check.

    Returns:
        function: The decorated function.

    Raises:
        None

    """

    def _function(request, *args, **kwargs):
        """
        Inner function that performs the permission and manager check.

        Args:
            request (HttpRequest): The request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            HttpResponse: The response from the decorated function.
        """
        user = request.user
        employee = getattr(user, "employee_get", None)
        is_manager = (
            employee is not None
            and Recruitment.objects.filter(recruitment_managers=employee).exists()
        )
        if user.has_perm(perm) or is_manager:
            return function(request, *args, **kwargs)
        messages.info(request, "You dont have permission.")
        previous_url = request.META.get("HTTP_REFERER", "/")
        script = f'<script>window.location.href = "{previous_url}"</script>'
        key = "HTTP_HX_REQUEST"
        if key in request.META.keys():
            return render(request, "decorator_404.html")
        return HttpResponse(script)

    return _function


@decorator_with_arguments
def view_permission_or_department_head(function, perm):
    """
    Like permission_required, but also lets department heads consult the
    recruitment pages (view permissions only); the view itself restricts the
    data to the recruitments of their departments.
    """

    def _function(request, *args, **kwargs):
        user = request.user
        if user.has_perm(perm) or (
            perm in DEPARTMENT_HEAD_PERMS and is_department_head(user)
        ):
            return function(request, *args, **kwargs)
        messages.info(request, "You dont have permission.")
        previous_url = request.META.get("HTTP_REFERER", "/")
        key = "HTTP_HX_REQUEST"
        if key in request.META.keys():
            return render(request, "decorator_404.html")
        script = f'<script>window.location.href = "{previous_url}"</script>'
        return HttpResponse(script)

    return _function


def candidate_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):

        if request.user.has_perm("recruitment.view_candidate"):
            return view_func(request, *args, **kwargs)
        if request.user:
            if request.user.is_authenticated:
                if (
                    request.user.employee_get.stage_set.exists()
                    or request.user.employee_get.recruitment_set.exists()
                ):
                    return view_func(request, *args, **kwargs)

        if "candidate_id" in request.session:
            return view_func(request, *args, **kwargs)
        return redirect("candidate-login")

    return _wrapped_view
