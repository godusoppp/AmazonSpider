import re
import requests
from scrapy import signals
from itemadapter import is_item, ItemAdapter
from Amazon.userAgents import get_random_ua
from Amazon.settings import DOMAIN_LIST, AGAINST_TEXT
import time
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message


proxy_dict = {"amazon.com": "us", "amazon.de": "de", "amazon.co.uk": "gb"}
# DOMAIN_LIST = ['amazon.com', "amazon.de", "amazon.co.uk"]
proxy_api = "http://192.168.6.25:5000/proxyInfo"
resp = requests.get(proxy_api).json()


class MyRetryMiddleware(RetryMiddleware):

    """
    404不存在此页面，结束不进行
    非200页面，等待10秒后进行重试
    domain_list
    domain_against_texts
    属于检测是否被识别机器人
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.max_retry_times = 4

    def process_response(self, request, response, spider):
        # print(response.status)
        # print(request.headers)
        if response.status == 404:
            return response

        if response.status != 200:
            reason = response_status_message(response.status)
            time.sleep(3)
            return self._retry(request, reason, spider) or response

        for domain in DOMAIN_LIST:
            if request.url.find(domain) != -1:
                against_text_list = AGAINST_TEXT[domain]
                for against_text in against_text_list:
                    if response.text.find(against_text) != -1:

                        request.meta['retry_time'] += 1

                        change_ip_port = request.meta['change_ip_port']
                        print("修改ip")
                        requests.get("http://192.168.6.25:5000/switchIp?controlPort={}".format(change_ip_port))
                        agent = get_random_ua()
                        request.headers['user-agent'] = agent
                        time.sleep(1.5)
                        return self._retry(request, "被检测到反爬", spider) or response
                return response


class AmazonSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        """
        检测属于哪个域名获取对应地区代理
        """
        try:
            print(request.meta['retry_time'])
        except KeyError:
            request.meta['retry_time'] = 0
        proxy = None
        for domain in DOMAIN_LIST:
            if request.url.find(domain) != -1:
                country = proxy_dict[domain]
                for proxy_info in resp:
                    if proxy_info['ExitNodes'] == country:
                        proxy = proxy_info['proxies']
                        request.meta['change_ip_port'] = proxy_info['controlPort']
                        break

        if proxy:
            proxy = proxy['https']
            request.meta['proxy'] = proxy

        else:
            request.meta['proxy'] = "https://192.168.6.25:8003"
        # print(request.meta['proxy'])
        request.headers['user-agent'] = get_random_ua()
        if request.meta['retry_time'] == 3:
            request.meta['proxy'] = "https://192.168.6.25:8003"


    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    def process_start_requests(self, start_requests, spider):
        # Called with the start requests of the spider, and works
        # similarly to the process_spider_output() method, except
        # that it doesn’t have a response associated.

        # Must return only requests (not items).
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)


class AmazonDownloaderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the downloader middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.

        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        # Called for each request that goes through the downloader
        # middleware.

        # Must either:
        # - return None: continue processing this request
        # - or return a Response object
        # - or return a Request object
        # - or raise IgnoreRequest: process_exception() methods of
        #   installed downloader middleware will be called
        return None

    def process_response(self, request, response, spider):
        # Called with the response returned from the downloader.

        # Must either;
        # - return a Response object
        # - return a Request object
        # - or raise IgnoreRequest
        return response

    def process_exception(self, request, exception, spider):
        # Called when a download handler or a process_request()
        # (from other downloader middleware) raises an exception.

        # Must either:
        # - return None: continue processing this exception
        # - return a Response object: stops process_exception() chain
        # - return a Request object: stops process_exception() chain
        pass

    def spider_opened(self, spider):
        spider.logger.info('Spider opened: %s' % spider.name)
