from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from apps.news.models import Category, Post

def home(request):
    featured = Post.objects.visible_to(request.user).filter(featured=True).first()
    latest_posts = Post.objects.visible_to(request.user)[:6]
    opportunities = Post.objects.visible_to(request.user).filter(
        is_opportunity=True
    )[:3]
    categories = Category.objects.filter(active=True)[:8]
    return render(request, 'core/home.html', {
        'featured': featured,
        'latest_posts': latest_posts,
        'opportunities': opportunities,
        'categories': categories,
    })

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')

def health(request):
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        cursor.fetchone()
    return JsonResponse({'status': 'ok', 'service': 'abasc_mvp1'})

def error_403(request, exception=None):
    return render(request, 'errors/403.html', status=403)

def error_404(request, exception=None):
    return render(request, 'errors/404.html', status=404)

def error_500(request):
    return render(request, 'errors/500.html', status=500)
