from django.shortcuts import render
from horilla.decorators import (
    delete_permission,
    duplicate_permission,
    hx_request_required,
    login_required,
    manager_can_enter,
    permission_required,
)

# Create your views here.

@login_required
def fil_actualite_view(request):
    return render(request, "fil/fil_actualite.html")
 