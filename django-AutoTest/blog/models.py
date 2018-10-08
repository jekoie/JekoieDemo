from django.db import models
from django.conf import settings
from django.utils import timezone
from ckeditor_uploader.fields import RichTextUploadingField
# Create your models here.

class PublisheManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status='published')

class Article(models.Model):
    ARTICLE_STATUS = [
        ('draft', '草稿'),
        ('published', '发布')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='article', verbose_name='用户')
    title = models.CharField('标题', max_length=254, default='', unique_for_date='created')
    body = RichTextUploadingField('正文', default='', config_name='front')
    published = models.DateTimeField('发布时间', default=timezone.now)
    created = models.DateTimeField('创建时间', auto_now_add=True)
    updated = models.DateTimeField('更新时间', auto_now=True)
    reads = models.PositiveIntegerField('阅读数量', default=0)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='likes', blank=True, verbose_name='点赞数量')
    status = models.CharField('状态', max_length=10, choices=ARTICLE_STATUS, default='draft')
    collect = models.ManyToManyField(settings.AUTH_USER_MODEL, through='ArticleRelation',
                                     through_fields=('article', 'user'), verbose_name='收藏的用户', related_name='collect')

    objects = models.Manager()
    publishedqt = PublisheManager()

    class Meta:
        ordering = ['-published']
        verbose_name = '用户文章'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

class ArticleRelation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='article_relation', verbose_name='用户')
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='article_relation', verbose_name='用户文章')
    created = models.DateTimeField('创建时间' ,auto_now_add=True)

    class Meta:
        verbose_name = '收藏的用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.user.username + ' ' + self.article.title

