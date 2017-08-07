# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import tablib
from items import GanjiItem

class GanjiPipeline(object):
    def __init__(self):
        self.dataset  = tablib.Dataset(headers=['title', 'size', 'address', 'info', 'feature'])

    def process_item(self, item, spider):
        row_data = [ item[key] for key in self.dataset.headers ]
        self.dataset.lpush(row_data)
        return item

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        with open('t.xls', 'wb+') as f:
            f.write(self.dataset.xls)
