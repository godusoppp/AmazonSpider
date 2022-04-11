import scrapy
import re
import time
from scrapy import Request


class ProductInfoSpider(scrapy.Spider):
    name = 'product_info'
    allowed_domains = ['amazon.com',"amazon.de","amazon.co.uk"]
    start_urls = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_file_path = getattr(self, "config", None)
        self.spider_asin_list = []
        with open(self.config_file_path,"r",encoding="utf-8") as f:
            line_index = 0
            for line in f:
                line_index += 1
                if line_index == 1:
                    continue
                line_list = line.split(",")
                site = line_list[0]
                asin = line_list[1].replace("\n", "")
                self.spider_asin_list.append({"site":site,"asin":asin})

    def start_requests(self):
        # for i, url in enumerate(self.start_urls):
        #     print(i,url)
        #     yield scrapy.Request(self.start_urls[0], meta={'cookiejar': i},
        #                          callback=self.main_page_req)
        for asin_info in self.spider_asin_list:
            yield Request('https://www.{}/dp/{}'.format(asin_info["site"],asin_info["asin"]), callback=self.parse)

    def main_page_req(self,response):

        yield Request('https://www.amazon.com/dp/B08N4XDQ5G', callback=self.parse,meta={'cookiejar': response.meta['cookiejar']})

    def parse(self, response):
        asin = re.match(".*?dp/(.{10})", response.url).group(1)
        print()
        site = re.match(".*?www.(.*)/dp/", response.url).group(1)
        try:
            # 标题
            title = response.xpath(".//span[@id='productTitle']/text()")[0].get().replace("\n", "")
        except IndexError:
            print("Title Error:", asin)
        shop_info = response.xpath(".//div[@id='merchant-info']//text()")
        if not shop_info:
            shop_info = response.xpath(".//div[@id='tabular_feature_div']//text()")

        if shop_info:
            all_text = ""
            for info in shop_info:
                all_text += info.get()

            if re.match("[\s\S]*?Amazon", all_text):
                ships_from = "fba"
            else:
                ships_from = "fbm"
        else:
            ships_from = "fbm"

        # 评价数量 需要捕获无货或者剩余一件
        try:
            comment_number = response.xpath(".//span[@id='acrCustomerReviewText']/text()")[0].get().replace(" ratings",
                                                                                                  "")
        except IndexError:
            comment_number = "0"
        try:
            star_number = response.xpath(".//span[@id='acrPopover']//span[@class='a-icon-alt']/text()")[0].get()
        except IndexError:
            star_number = None
        try:
            price = response.xpath(".//span[@id='priceblock_ourprice']/text()")
            if price:
                price = price[0].get()
            else:
                price = response.xpath(".//span[@id='priceblock_dealprice']/text()")
            if price:
                price = price[0].get()
            else:
                price = response.xpath(".//span[contains(@class,'apexPriceToPay')]//text()")
            if price:
                price = price[0].get()
            else:
                price = response.xpath(".//span[contains(@class,'priceToPay')]//text()")
                price = price[0].get()
        except IndexError:
            try:
                price = response.xpath(".//div[@id='availability']/span/text()")[0]
                # price = None
                # if re.match("[\s\S]*?Only 1 left in stock", price_info):
                #     cart_api = "https://www.amazon.com/gp/aod/ajax/ref=dp_aod_unknown_mbc?asin=" + asin
                #     res = session.get(cart_api, timeout=20).text
                #     cart_tree = etree.HTML(res)
                #     price = cart_tree.xpath(".//span[@class='a-price']/span/text()")[0]
                # elif re.match("[\s\S]*?Currently unavailable", price_info):
                #     price = None
                # else:
                #     price = None
            except IndexError:
                price = None
        img_element = response.xpath(".//div[@id='imgTagWrapperId']/img/@src")
        if img_element:
            img_url = img_element[0].get()
        else:
            print("图片出现问题:", asin)
            img_url = None
        # 热卖排行 发布日期 品牌信息
        if site == "amazon.de":
            BSR_match_string = "Amazon Bestseller-Rang"
            date_first_available_match_string = "Im Angebot von Amazon.de seit"
            brand_match_string = "Marke"
        else:
            BSR_match_string = "Best Sellers Rank"
            date_first_available_match_string = "Date First Available"
            brand_match_string = "Brand"
        product_detail_table = response.xpath(".//table[@id='productDetails_detailBullets_sections1']//tr")
        date_first_available = None
        best_seller_ranks = ""
        for th_and_td in product_detail_table:
            info_key = "".join(th_and_td.xpath("./th/text()").get()).replace("\n", "")
            info_value = "".join(th_and_td.xpath("./td//text()").get()).replace("\n", "")
            if re.match("[\s\S]*?%s" % BSR_match_string, info_key):
                br_elements  = th_and_td.xpath("./td//br")
                if br_elements:
                    for br_element in br_elements:
                        best_seller_ranks += "".join(
                            br_element.xpath("./preceding-sibling::span[1]//text()").get()) + br_element.xpath("./preceding-sibling::span[1]/a/text()").get() + "\n"
                    best_seller_ranks = best_seller_ranks[0:-1]
                else:
                    best_seller_ranks = info_value
            if re.match("[\s\S]*?%s" % date_first_available_match_string, info_key):
                date_first_available = info_value
        if not best_seller_ranks:
            best_seller_ranks = None
        product_overview_table = response.xpath(".//div[@id='productOverview_feature_div']//tr")
        brand = None
        for td1_and_td2 in product_overview_table:
            info_key = "".join(td1_and_td2.xpath("./td[1]//text()").get()).replace("\n", "")
            info_value = "".join(td1_and_td2.xpath("./td[2]//text()").get()).replace("\n", "")
            if re.match("[\s\S]*?%s" % brand_match_string, info_key):
                brand = info_value
                break
        timestamp = str(int(time.time()))

        product_dir = { "asin": asin, "title": title,
                       "customer_review": comment_number,
                       "price": price,
                       "img_url": img_url, "star_rating": star_number, "ships_from": ships_from,
                       "shop_name": None, "best_sellers_rank": best_seller_ranks, "brand": brand,
                       "date_first_available": date_first_available, "create_time": timestamp,
                       "site": site}
        yield product_dir
