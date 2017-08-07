# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy
import re
from string import maketrans
from scrapy import Field
from scrapy.loader.processors import TakeFirst, Join, MapCompose

def remove_blank(value):
    #print 'value', type(value), value, [value]
    value = value.replace('\n', ' ')
    value = value.replace('\t', ' ')
    return re.sub(' +', ' ',  value)


class LianjiaItem(scrapy.Item):
    link = Field(output_processor=Join())
    title = Field(output_processor=Join())
    where = Field(output_processor=Join())
    area = Field(input_processor=MapCompose(remove_blank), output_processor=Join())
    other = Field(input_processor=MapCompose(remove_blank), output_processor=Join())
    type = Field(input_processor=MapCompose(remove_blank), output_processor=Join())
    average = Field(input_processor=MapCompose(remove_blank), output_processor=Join())
    sum = Field(input_processor=MapCompose(remove_blank), output_processor=Join())
