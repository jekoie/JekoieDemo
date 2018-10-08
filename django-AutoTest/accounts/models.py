from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from easy_thumbnails.fields import ThumbnailerImageField
# Create your models here.

def validate_phone(value):
    if  not (value.startswith('1') and len(value) == 11 ) :
        raise ValidationError('请输入正确的电话号码', code='invalid', params={'value': value})
    return value

def validate_email(value):
        if not value.endswith('@mailraisecomsz.com'):
            raise ValidationError('请输入RAISECOM内部邮箱(someone@mailraisecomsz.com)', code='invalid', params={'value': value})
        return value

class User(AbstractUser):
    DEPARMENT_CHOICE = [
        ('craft', '工艺部'),
        ('executive', '行政部'),
        ('personnel', '人事部'),
        ('quality', '质量部'),
        ('service', '客服部'),
        ('planer', '计划部'),
        ('purchaser', '采购部'),
        ('producter', '成品部'),
        ('finance', '财务部'),
        ('manufacture1', '制造一部'),
        ('manufacture2', '制造二部'),
        ('maintain', '售后维修部'),
        ('dispatcher', '生产调度部'),
    ]
    chinese_name = models.CharField('姓名', max_length=254, default='你的名字')
    email = models.EmailField('Email', validators=[validate_email])
    phone = models.CharField('电话', max_length=254, validators=[validate_phone], help_text='输入11位电话号码')
    photo = ThumbnailerImageField('图像', upload_to='users/', blank=True, resize_source={'size': (100, 100), 'sharpen':True})
    deparment = models.CharField('部门', max_length=100, choices=DEPARMENT_CHOICE, default='craft')
    addr = models.CharField('地址',max_length=254, blank=True)

    class Meta(AbstractUser.Meta):
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        permissions = [
            ('can_view', 'can view'),
        ]

    def __str__(self):
        return self.username