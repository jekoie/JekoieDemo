from django.conf import settings
from django.db import models
from easy_thumbnails.fields import  ThumbnailerImageField
from django.utils import timezone
# Create your models here.

class SNModel(models.Model):
    id = models.AutoField(primary_key=True)
    sn = models.CharField('SN', max_length=255,  db_index=True )
    result = models.CharField('结果' ,max_length=255, db_index=True)
    starttime = models.DateTimeField('起始时间')
    endtime = models.DateTimeField('结束时间')

    totaltime = models.CharField('总时间', max_length=255, null=True, blank=True)
    operator = models.CharField('操作员', max_length=255, null=True, blank=True)
    workorder = models.CharField('工单号', max_length=255, null=True, blank=True)
    bomcode = models.CharField('BOM' ,max_length=255, null=True, blank=True)
    productname = models.CharField('产品名称' ,max_length=255, null=True, blank=True)
    productver = models.CharField('产品版本', max_length=255, null=True, blank=True)
    lotno = models.CharField('批次号' ,max_length=255, null=True, blank=True)
    guid = models.CharField(max_length=255, null=True, blank=True)
    description = models.CharField('', max_length=255, null=True, blank=True)
    logserial = models.TextField('串口日志', null=True, blank=True)
    logprocess = models.TextField('过程日志', null=True, blank=True)
    segment_text = models.TextField( null=True, blank=True)
    segment1 = models.CharField('MAC', max_length=255, null=True, blank=True)
    segment2 = models.CharField('物料代码', max_length=255, null=True, blank=True)
    segment3 = models.CharField('工序', max_length=255, null=True, blank=True)
    segment4 = models.CharField('线体', max_length=255, null=True, blank=True)
    segment5 = models.CharField('', max_length=255, null=True, blank=True)
    segment6 = models.CharField(max_length=255, null=True, blank=True)
    segment7 = models.CharField(max_length=255, null=True, blank=True)
    segment8 = models.CharField(max_length=255, null=True, blank=True)
    segment9 = models.CharField(max_length=255, null=True, blank=True)
    segment10 = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'sn_table'
        verbose_name = 'SN数据'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.sn

class AutoSoftModel(models.Model):
    id = models.AutoField(primary_key=True)
    softname =  models.CharField('软件名称', max_length=255, null=True, blank=True)
    author = models.CharField('作者', max_length=255, null=True, blank=True)
    version = models.CharField('版本', max_length=255, null=True, blank=True, db_index=True)
    path = models.CharField('路径', max_length=255, null=True, blank=True)
    segment1 = models.CharField( max_length=255, null=True, blank=True)
    segment2 = models.CharField( max_length=255, null=True, blank=True)
    segment3 = models.CharField( max_length=255, null=True, blank=True)
    segment4 = models.CharField( max_length=255, null=True, blank=True)
    segment5 = models.CharField( max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'soft_table'
        verbose_name = 'AutoTest软件版本管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.softname

class SoftwareModel(models.Model):
    SOFTTYPE = [
        ('autotest', 'AutoTest平台软件'),
        ('other', '其他软件')
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    softname = models.CharField('软件名称', max_length=254, unique=True)
    softtype = models.CharField('软件类型', max_length=254, choices=SOFTTYPE)
    description = models.TextField('描述')
    file = models.FileField('文件', upload_to='software/')
    created = models.DateTimeField('创建时间', auto_now_add=True)
    updated = models.DateTimeField('修改时间', auto_now=True)
    published = models.DateTimeField('发布时间', default=timezone.now)
    download_counts = models.PositiveIntegerField('下载次数', default=0)

    class Meta:
        ordering = ['-published']
        verbose_name = '软件管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.softname


class Website(models.Model):
    name = models.CharField('名称', max_length=254)
    url = models.URLField('网址')
    image = ThumbnailerImageField( '图像', upload_to='websites/', blank=True, resize_source={'size':(100, 100), 'sharpen':True})
    description = models.TextField('描述', blank=True)
    created = models.DateTimeField('创建时间', auto_now_add=True)
    updated = models.DateTimeField('修改时间', auto_now=True)
    published = models.DateTimeField('发布时间', default=timezone.now)

    class Meta:
        ordering = ['-published']
        verbose_name = '网站'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

