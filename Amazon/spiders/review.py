import re

import scrapy
from scrapy import Request


class ReviewSpider(scrapy.Spider):
    name = 'review'
    allowed_domains = ['amazon.com', 'amazon.de', 'amazon.co.uk']
    start_urls = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.config_file_path = getattr(self, "config", None)
        self.spider_asin_list = []
        with open(self.config_file_path, "r", encoding="utf-8") as f:
            line_index = 0
            for line in f:
                line_index += 1
                if line_index == 1:
                    continue
                line_list = line.split(",")
                site = line_list[0]
                asin = line_list[1].replace("\n", "")
                self.spider_asin_list.append({"site": site, "asin": asin})

    def start_requests(self):
        for i, asin_info in enumerate(self.spider_asin_list):
            asin = asin_info['asin']
            site = asin_info['site']
            url = "https://www.{}/product-reviews/{}".format(site, asin)
            yield Request(url=url, callback=self.get_comment_number,
                          meta={"asin": asin, "site": site})
            # return

    def get_comment_number(self, response):
        with open("./check.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        site = response.meta['site']
        asin = response.meta['asin']
        comment_elements = response.xpath(".//div[@data-hook='cr-filter-info-review-rating-count']//text()")
        comment_texts = ""
        for comment_text in comment_elements:
            comment_texts += comment_text.get()
        comment_number = re.match("[\s\S]*?global ratings \| ([\s\S]*?) global reviews", comment_texts)
        if not comment_number:
            comment_number = re.match("[\s\S]*?Gesamtbewertungen,([\s\S]*?) mit Rezensionen", comment_texts)
        if not comment_number:
            comment_number = re.match("[\s\S]*?globale Bewertungen \| ([\s\S]*?) globale Rezensionen", comment_texts)
        #     3,446 total ratings, 620 with reviews
        if not comment_number:
            comment_number = re.match("[\s\S]*?total ratings, ([\s\S]*?) with reviews", comment_texts)
        comment_number = comment_number.groups(1)[0].replace(",", "")
        # 德国站 3.419 Gesamtbewertungen,612 mit Rezensionen
        # print("comment_number:",comment_number)
        all_page = int(comment_number) / 20
        if all_page >= int(all_page):
            all_page = int(all_page) + 1
        else:
            all_page = int(all_page)
        for page_number in range(1, all_page + 2):

            reviews_url = "https://www.{}/hz/reviews-render/ajax/reviews/get/ref=cm_cr_arp_d_paging_btm_next_{}".format(
                site, page_number)
            string_data = """sortBy=recent&reviewerType=all_reviews&formatType=&mediaType=&filterByStar=&pageNumber={}&filterByLanguage=&filterByKeyword=&shouldAppend=undefined&deviceType=desktop&canShowIntHeader=undefined&reftag=cm_cr_getr_d_paging_btm_next_{}&pageSize=20&asin={}&scope=reviewsAjax1""".format(
                page_number, page_number, asin)
            if response.meta['retry_time'] == 3:
                meta = {"retry_time": 3,"site":site,"asin":asin}
            else:
                meta = {"site":site,"asin":asin}
            yield Request(method='POST', url=reviews_url, body=string_data, callback=self.parse, meta=meta,
                          headers={"content-type": "application/x-www-form-urlencoded;charset=UTF-8"})

    def parse(self, response, **kwargs):
        # with open("./check.html", "w", encoding="utf-8") as f:
        #     f.write(response.text)
        site = response.meta['site']
        asin = response.meta['asin']
        for review_element in response.xpath(".//div[@data-hook='\\\"review\\\"']"):
            title = "".join(review_element.xpath(".//a[@data-hook='\\\"review-title\\\"']//text()").getall()).replace(
                "\\n", " ").strip()
            review = "".join(
                review_element.xpath(".//span[@data-hook='\\\"review-body\\\"']//text()").getall()).replace("\\n",
                                                                                                            " ").strip()

            author = "".join(
                review_element.xpath(".//div[@data-hook='\\\"genome-widget\\\"']//text()").getall()).replace("\\n",
                                                                                                             "").strip()
            date = "".join(review_element.xpath(".//span[@data-hook='\\\"review-date\\\"']//text()").getall()).replace(
                "\\n",
                "").strip()
            style = "|".join(review_element.xpath(".//a[@data-hook='\\\"format-strip\\\"']//text()").getall()).replace(
                "\\n",
                "").strip()
            purchased = "".join(
                review_element.xpath(".//span[@data-hook='\\\"avp-badge\\\"']//text()").getall()).replace("\\n",
                                                                                                          "").strip()
            helpful_number = "".join(
                review_element.xpath(".//span[@data-hook='\\\"helpful-vote-statement\\\"']//text()").getall()).replace(
                "\\n",
                "").strip()
            star = "".join(review_element.xpath(".//span[@class='\\\"a-icon-alt\\\"']//text()").getall()).replace("\\n",
                                                                                                                  "").strip()
            # img_list = "|".join(
            #     text.attrib['src'] for text in review_element.xpath(".//img[@alt='\\\"Customer image\\\"']"))
            img_list = "|".join(
                text.get().replace("\\\\\"","") for text in review_element.xpath(".//img[@alt='\\\"Customer']/@src"))
            item = {"asin":asin,"site":site,"star":star,"title":title,"review":review,"purchased":purchased,"date":date,"style":style,"author":author,"helpful_number":helpful_number,"img_list":img_list}
            yield item
