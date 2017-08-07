# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import tablib
import datetime
from items import LianjiaItem

class LianjiaPipeline(object):
    def __init__(self):
        self.filename = str(datetime.date.today())
        self.dataset = tablib.Dataset(headers=LianjiaItem.fields.keys())

    def process_item(self, item, spider):
        for key in self.dataset.headers:
            if key not in item.keys():
                item[key] = ''

        row_data = [item[key] for key in self.dataset.headers]
        self.dataset.lpush(row_data)
        return item

    def open_spider(self, spider):
        pass

    def close_spider(self, spider):
        with open(self.filename + '.xls', 'wb+') as f:
            f.write(self.dataset.xls)