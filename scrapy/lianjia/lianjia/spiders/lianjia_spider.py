import scrapy
from ..items import LianjiaItem
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy_splash import SplashRequest
from scrapy.loader import ItemLoader

class FangSpider(CrawlSpider):
    name = 'lianjia'
    rules = [Rule(LinkExtractor(allow=(r'/loupan/pg\d+/') ), follow=True , process_request='splash_request')]

    def start_requests(self):
        urls = ['http://sz.fang.lianjia.com/loupan/']
        yield SplashRequest(urls[0], args={'wait': 0.5} )

    def splash_request(self, request):
        return SplashRequest(request.url, args={'wait': 0.5})

    def parse_start_url(self, response):
        houses = response.xpath('//ul[@id="house-lst"]/li')
        for house in houses:
            il = ItemLoader(LianjiaItem(), selector=house)
            il.add_xpath('link', './div[@class="pic-panel"]/a/@href')
            il.add_xpath('title', './div[@class="info-panel"]/div[@class="col-1"]//a/text()')
            il.add_xpath('where', './div[@class="info-panel"]/div[@class="col-1"]/div[@class="where"]/span/text()')
            il.add_xpath('area', './div[@class="info-panel"]/div[@class="col-1"]/div[@class="area"]//text()')
            il.add_xpath('other', './div[@class="info-panel"]/div[@class="col-1"]/div[@class="other"]/span/text()')
            il.add_xpath('type', './div[@class="info-panel"]/div[@class="col-1"]/div[@class="type"]/span/text()')
            il.add_xpath('average', './/div[@class="price"]/div[@class="average"]//text()')
            il.add_xpath('sum', './/div[@class="price"]/div[@class="sum-num"]//text()')
            yield il.load_item()

    def _requests_to_follow(self, response):
        seen = set()
        for n, rule in enumerate(self._rules):
            links = [lnk for lnk in rule.link_extractor.extract_links(response)
                     if lnk not in seen]
            if links and rule.process_links:
                links = rule.process_links(links)
            for link in links:
                seen.add(link)
                r = self._build_request(n, link)
                yield rule.process_request(r)