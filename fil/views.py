from django.shortcuts import render

# Create your views here.

def fil_actualite_view(request):
    return render(request, "fil/fil_actualite.html")
 