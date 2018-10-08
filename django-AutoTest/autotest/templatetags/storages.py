from django import template
from datetime import timedelta

register = template.Library()

@register.simple_tag
def get_size(fs, name):
    return fs.size(name)

@register.simple_tag
def judge_exists(fs, name):
    return fs.exists(name)

@register.simple_tag
def get_modified_time(fs, name):
    try:
        orign_time = fs.modified_time(name)
        localtime = orign_time + timedelta(hours=8)
    except Exception as e:
        localtime = 0
    return localtime