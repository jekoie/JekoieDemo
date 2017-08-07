#coding:utf-8
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.loader import ItemLoader
from ..items import GanjiItem

class GanjiSpider(CrawlSpider):
    name = 'ganji'
    rules = [Rule( LinkExtractor(allow=('/o\d+'), restrict_xpaths=('//div[@class="f-page"]//a') ), callback='parse_item' , follow=True)]
    allowed_domains = ['sz.ganji.com']
    start_urls = ['http://sz.ganji.com/fang5/']

    def parse_start_url(self, response):
        pass
      #  print '--start', response.url

    def parse_item(self, response):
        houses =  response.xpath('//div[@class="f-main-list"]//div[@class="f-list-item ershoufang-list"]')

        for house in houses:
            l = ItemLoader(item=GanjiItem(), selector=house)
            l.add_css('title', 'dd.dd-item.title a::text')
            l.add_css('size', 'dd.dd-item.size span::text')
            l.add_css('address', 'dd.dd-item.address span ::text')
            l.add_css('feature', 'dd.dd-item.feature span::text')
            l.add_css('info', 'dd.dd-item.info div ::text')
            yield l.load_item()