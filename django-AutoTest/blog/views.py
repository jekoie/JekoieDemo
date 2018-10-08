from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from autotest.decorators import ajax_required
from django.contrib.auth import get_user_model
from .models import Article, ArticleRelation
from .forms import SearchForm, CreateArticleForm
# Create your views here.


@login_required
def diary_list(request, collect=False):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            search_title = form.cleaned_data['search']
            all_articles = Article.objects.filter(title__icontains=search_title)
    else:
        all_articles = Article.objects.filter(user=request.user)

    form = SearchForm()
    page = request.GET.get('page', 1)
    paginator = Paginator(all_articles, 20)
    try:
        articles = paginator.get_page(page)
    except PageNotAnInteger:
        articles = paginator.get_page(1)
    except EmptyPage:
        articles = paginator.get_page(paginator.num_pages)

    return render(request, 'blog/diary.html', {'articles': articles, 'form': form})

@login_required
def diary_collect_list(request):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            search_title = form.cleaned_data['search']
            all_articles = request.user.collect.filter(title__icontains=search_title)
    else:
        all_articles = request.user.collect.all()

    form = SearchForm()
    page = request.GET.get('page', 1)
    paginator = Paginator(all_articles, 20)
    try:
        articles = paginator.get_page(page)
    except PageNotAnInteger:
        articles = paginator.get_page(1)
    except EmptyPage:
        articles = paginator.get_page(paginator.num_pages)

    return render(request, 'blog/blog_list.html', {'articles': articles, 'form': form})

@login_required
def diary_detail(request, id):
    article = Article.objects.get(id=id)
    article.reads += 1
    article.save()
    return render(request, 'blog/diary_detail.html', {'article': article})

@login_required
def create_diary(request, id):
    try:
        article = Article.objects.get(user=request.user, id=request.POST.get('article_id', id))
    except Exception:
        article = Article(user=request.user)

    if request.method == 'POST':
        form = CreateArticleForm( instance=article, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '保存成功')
        else:
           return render(request, 'blog/create_article.html', {'form': form})

    form = CreateArticleForm(instance=article)
    return render(request, 'blog/create_article.html', {'form': form})


@login_required
def remove_diary(request, id):
    try:
        article = Article.objects.get(id=id)
        article.delete()
    except Exception:
        messages.error(request, '删除失败')

    messages.success(request, '删除成功')
    return redirect('blog:diary_list')

@login_required
def publish_diary(request, id, status):
    try:
        article = Article.objects.get(id=id)
        article.status = status
        article.published = timezone.now()
        article.save()
    except Exception:
        messages.error(request, '发布失败')

    messages.success(request, '发布成功')
    return redirect('blog:blog_list')

def blog_list(request, username=None):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            search_title = form.cleaned_data['search']
            if username:
                all_articles = Article.publishedqt.filter(title__icontains=search_title, user__username=username)
            else:
                all_articles = Article.publishedqt.filter(title__icontains=search_title)
    else:
        if username:
            all_articles = Article.publishedqt.filter(user__username=username)
        else:
            all_articles = Article.publishedqt.all()
    form = SearchForm()
    page = request.GET.get('page', 1)
    paginator = Paginator(all_articles, 20)
    try:
        articles = paginator.get_page(page)
    except PageNotAnInteger:
        articles = paginator.get_page(1)
    except EmptyPage:
        articles = paginator.get_page(paginator.num_pages)
    if username:
        username = get_user_model().objects.get(username=username)
        username = username.chinese_name
    return render(request, 'blog/blog_list.html', {'articles': articles, 'form': form, 'username': username})

def blog_detail(request, id):
    article = Article.publishedqt.get(id=id)
    if request.user.is_authenticated and article.user == request.user:
        return redirect('blog:diary_detail', id=article.id)
    article.reads += 1
    article.save()
    return render(request, 'blog/blog_detail.html', {'article': article})

@login_required
@ajax_required
@require_POST
def blog_like(request):
    id, action = request.POST.get('id'), request.POST.get('action')
    if id and action and 'like' in action:
        article = Article.objects.get(id=id)
        if action == 'like':
            article.likes.add(request.user)
        elif action == 'unlike':
            article.likes.remove(request.user)
    elif id and action and 'collect' in action:
        article = Article.objects.get(id=id)
        if action == 'collect':
            ArticleRelation.objects.get_or_create(user=request.user, article=article)
        elif action == 'uncollect':
            ArticleRelation.objects.get(user=request.user, article=article).delete()
    return JsonResponse({'status': 'ok'})

