from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import (
    require_http_methods,
    require_POST,
)

from apps.accounts.decorators import executive_required
from apps.core.models import AuditLog
from apps.core.services import log_action
from .forms import CategoryForm, PostForm
from .models import Category, Post
from .services import StorageUploadError, upload_news_image

def post_list(request):
    posts = Post.objects.visible_to(request.user)
    category_slug = request.GET.get('categoria', '').strip()
    query = request.GET.get('q', '').strip()
    opportunities_only = (
        request.GET.get('oportunidades') == '1'
    )

    if category_slug:
        posts = posts.filter(category__slug=category_slug)
    if query:
        posts = posts.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(body__icontains=query)
        )
    if opportunities_only:
        posts = posts.filter(is_opportunity=True)

    page = Paginator(posts, 9).get_page(request.GET.get('page'))
    return render(request, 'news/list.html', {
        'page_obj': page,
        'categories': Category.objects.filter(active=True),
        'selected_category': category_slug,
        'query': query,
        'opportunities_only': opportunities_only,
    })

def post_detail(request, slug):
    post = get_object_or_404(
        Post.objects.visible_to(request.user),
        slug=slug,
    )
    related = Post.objects.visible_to(request.user).filter(
        category=post.category
    ).exclude(pk=post.pk)[:3]
    return render(
        request,
        'news/detail.html',
        {'post': post, 'related': related},
    )

@executive_required
def manage_posts(request):
    posts = Post.objects.select_related('category', 'author').all()
    status = request.GET.get('status')
    if status in dict(Post.Status.choices):
        posts = posts.filter(status=status)
    return render(request, 'news/manage_list.html', {
        'posts': posts,
        'selected_status': status,
    })

@executive_required
@require_http_methods(['GET', 'POST'])
def create_post(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        image = form.cleaned_data.get('image_file')
        if image:
            try:
                post.image_url = upload_news_image(image, request)
            except StorageUploadError as exc:
                form.add_error('image_file', str(exc))
                return render(request, 'news/form.html', {
                    'form': form,
                    'page_title': 'Nova publicação',
                })
        post.save()
        log_action(
            request,
            AuditLog.Action.CREATE,
            f'Publicação criada: {post.title}',
            'Post',
            post.pk,
        )
        messages.success(request, 'Publicação criada com sucesso.')
        return redirect('news:manage')
    return render(request, 'news/form.html', {
        'form': form,
        'page_title': 'Nova publicação',
    })

@executive_required
@require_http_methods(['GET', 'POST'])
def update_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = PostForm(
        request.POST or None,
        request.FILES or None,
        instance=post,
    )
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        image = form.cleaned_data.get('image_file')
        if image:
            try:
                post.image_url = upload_news_image(image, request)
            except StorageUploadError as exc:
                form.add_error('image_file', str(exc))
                return render(request, 'news/form.html', {
                    'form': form,
                    'post': post,
                    'page_title': 'Editar publicação',
                })
        post.save()
        log_action(
            request,
            AuditLog.Action.UPDATE,
            f'Publicação atualizada: {post.title}',
            'Post',
            post.pk,
        )
        messages.success(request, 'Publicação atualizada.')
        return redirect('news:manage')
    return render(request, 'news/form.html', {
        'form': form,
        'post': post,
        'page_title': 'Editar publicação',
    })

@executive_required
@require_http_methods(['GET', 'POST'])
def delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if request.method == 'POST':
        title = post.title
        object_id = post.pk
        post.delete()
        log_action(
            request,
            AuditLog.Action.DELETE,
            f'Publicação excluída: {title}',
            'Post',
            object_id,
        )
        messages.success(request, 'Publicação excluída.')
        return redirect('news:manage')
    return render(
        request,
        'news/confirm_delete.html',
        {'post': post},
    )

@executive_required
@require_http_methods(['GET', 'POST'])
def categories(request):
    form = CategoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        category = form.save()
        log_action(
            request,
            AuditLog.Action.CREATE,
            f'Categoria criada: {category.name}',
            'Category',
            category.pk,
        )
        messages.success(request, 'Categoria criada.')
        return redirect('news:categories')
    return render(request, 'news/categories.html', {
        'form': form,
        'categories': Category.objects.all(),
    })

@executive_required
@require_POST
def toggle_publish(request, pk):
    post = get_object_or_404(Post, pk=pk)
    post.status = (
        Post.Status.DRAFT
        if post.status == Post.Status.PUBLISHED
        else Post.Status.PUBLISHED
    )
    post.save()
    log_action(
        request,
        AuditLog.Action.UPDATE,
        f'Status alterado: {post.title} → {post.get_status_display()}',
        'Post',
        post.pk,
    )
    messages.success(
        request,
        f'Publicação marcada como {post.get_status_display().lower()}.',
    )
    return redirect('news:manage')
