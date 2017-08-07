# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader.processors import Join, MapCompose, TakeFirst
from w3lib.html import remove_tags
from scrapy import Field
import re


def remove_blank(value):
    value = re.sub(' +', ' ', value.replace('\n', ' '))
    return value

class GanjiItem(scrapy.Item):
    title = Field(input_processor=MapCompose(remove_blank),
        output_processor=Join()
    )
    size = Field(input_processor=MapCompose(remove_blank), output_processor=Join())
    address = Field(
        input_processor=MapCompose(remove_blank),
        output_processor=Join())
    feature = Field(input_processor=MapCompose(remove_blank),output_processor=Join())
    info = Field(input_processor=MapCompose(remove_blank), output_processor=Join())
