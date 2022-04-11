import json
import scrapy
from scrapy import Request
import re
import logging
import time


class UkBsrSpider(scrapy.Spider):
    name = 'uk_bsr'
    allowed_domains = ['www.amazon.co.uk','amazon.co.uk']
    start_urls = ['https://www.amazon.co.uk/gp/bestsellers/?ref_=nav_cs_bestsellers']
    main_domain = "https://www.amazon.co.uk"
    finished_cate = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.level = int(getattr(self,"level",4))
        self.appoint = "Home & Kitchen"

    def start_requests(self):
        level = 0
        full_cate_name = "Any Department"
        yield Request(self.start_urls[0], callback=self.parse,meta={"page":1,"level":level,"full_cate_name":full_cate_name})

    def xhr_more_product(self, resp):
        try:
            html_text = resp.text
            script_list_string = re.match("[\s\S]*?data-client-recs-list=\"([\s\S]*?)\" data-index-offset",
                                          html_text).group(1)
            script_list_string = script_list_string.replace("&quot", '"').replace(";", "")
            script_list = json.loads(script_list_string)
            ids_list = []
            index_list = []
            for asin_info in script_list:
                if 30 <= script_list.index(asin_info) <= 50 or 80 <= script_list.index(asin_info) <= 100:
                    rank = asin_info['metadataMap']['render.zg.rank']
                    asin = asin_info["id"]
                    ids_string = "{\"id\":\"%s\",\"metadataMap\":{\"render.zg.rank\":\"%s\",\"render.zg.bsms.currentSalesRank\":\"\",\"render.zg.bsms.percentageChange\":\"\",\"render.zg.bsms.twentyFourHourOldSalesRank\":\"\"},\"linkParameters\":{}}" % (
                        asin, rank)
                    ids_list.append(ids_string)
                    index_list.append(int(rank))
            off_set = str(len(ids_list))
            xhr_post_prams = {
                "faceoutkataname": "GeneralFaceout",
                "ids": ids_list,
                "indexes": index_list,
                "linkparameters": "",
                "offset": off_set,
                "reftagprefix": "zg_bs_home-garden"
            }
            timestamp = int(time.time() + 152)
            headers_params = {
                "x-amz-acp-params": "tok=figYbBX4T_Bdr9RNKmS7c8UM5KIGYCHTuRkZ8I3-wjM;ts={};rid=7T63HY3PMWV6T3E9PT0V;d1=152;d2=0".format(
                    timestamp)}
            page = resp.meta["page"] + 1
            full_cate_name = resp.meta["full_cate_name"]
            run = Request(url="{}/acp/p13n-zg-list-grid-desktop/aunxwj8s308n53up/nextPage?".format(self.main_domain),
                          callback=self.get_products_from_cate_page, method="POST", headers=headers_params,
                          body=json.dumps(xhr_post_prams),dont_filter=True, meta={"page": page, "full_cate_name":full_cate_name})
            return run
        except Exception as e:
            print(e)
            print(e.__traceback__.tb_lineno)

    def parse(self, response):
        # with open("./check.html","w",encoding="utf-8") as f:
        #     f.write(response.text)
        level = response.meta["level"] + 1
        full_cate_name = response.meta["full_cate_name"]
        print(full_cate_name)
        top_cate_name_elements = response.xpath(".//div[@role='group']//div[@role='treeitem']")
        if not top_cate_name_elements:
            raise IndexError("页面出现错误")
        for top_cate in top_cate_name_elements:
            try:
                top_cate_url = top_cate.xpath("./a/@href")[0].get()
                if not re.match("[\s\S]*?%s" % self.main_domain, top_cate_url):
                    top_cate_url = self.main_domain + top_cate_url
                top_cate_name = "".join(top_cate.xpath(".//text()").get())
                if top_cate_name != self.appoint:
                    continue
                top_full_cate_name = full_cate_name + "~" + top_cate_name
                # if top_full_cate_name in self.finished_cate:
                #     return
                self.finished_cate.append(top_full_cate_name)
                logging.info("start:" + top_cate_url)
                if level >= self.level:
                    continue
                yield Request(top_cate_url,callback=self.parse, meta={"page":1,"level":level,"full_cate_name":top_full_cate_name})
            except Exception as e:
                print(e)

        product_elements = response.xpath(".//div[@id='gridItemRoot']")
        data_list = self.products_parse([], product_elements, 1, full_cate_name)
        for res in data_list:
            yield res
        run_fun = self.xhr_more_product(resp=response)
        yield run_fun
        page2_url = response.url + "&pg=2"
        yield Request(url=page2_url,callback=self.get_products_from_cate_page,meta={"full_cate_name":full_cate_name,"page":3})

    def get_products_from_cate_page(self, response):
        """
        解析页面中的商品信息
        response:
        full_cate_name: 此页面分类信息
        """
        # with open("./check2.html","w",encoding="utf-8") as f:
        #     f.write(response.text)
        page = response.meta["page"]
        full_cate_name = response.meta["full_cate_name"]
        product_elements = response.xpath(".//div[@id='gridItemRoot']")
        first_page_asin_list = []
        data_list = self.products_parse(first_page_asin_list, product_elements, page, full_cate_name)
        for res in data_list:
            yield res
        if page == 3:
            run_fun = self.xhr_more_product(response)
            yield run_fun

    def products_parse(self, first_page_asin_list, product_elements, page, full_cate_name):
        """
        解析商品信息
        :param first_page_asin_list: 检查元素是否存在第一页中，有则不存储
        :param product_elements: 商品信息etree对象
        :param page: 第几页
        :param full_cate_name: 商品分类信息
        :return:
        """
        if page == 1:
            rank_increment = 0
        elif page == 2:
            rank_increment = 30
        elif page == 3:
            rank_increment = 50
        elif page == 4:
            rank_increment = 80
        else:
            raise Exception("page error!")
        products_data_list = []
        asin_list = []
        for product in product_elements:
            try:
                url = product.xpath(".//span[@class='a-link-normal']/a[1]/@href")
                if url:
                    url = url[0].get()
                else:
                    url = product.xpath(".//a/@href")
                    if url:
                        url = url[0].get()
                    else:
                        url = ""
                asin_index = re.match("[\s\S]*?/dp/(.*?)/", url)
                if asin_index:
                    asin = asin_index.group(1)
                else:
                    asin = None
                if asin in first_page_asin_list:
                    continue
                img_url = product.xpath(".//img/@src")
                if img_url:
                    img_url = img_url[0].get()
                else:
                    img_url = None
                rank = product_elements.index(product) + 1 + rank_increment
                name = product.xpath(".//div[contains(@class,'_p13n-zg-list-grid-desktop_truncationStyles_p13n-sc-css-line-clamp-3__g3dy1')]/text()")
                if not name:
                    name = product.xpath(
                        ".//div[contains(@class,'p13n-sc-truncate p13n-sc-line-clamp-1')]/text()")
                if not name:
                    name = product.xpath(
                        ".//div[contains(@class,'p13n-sc-truncate-desktop-type2')]/@title")
                if not name:
                    name = product.xpath(
                        ".//div[contains(@class,'p13n-sc-truncate-desktop-type2')]/text()")
                if not name:
                    name = product.xpath(
                        ".//div[contains(@class,'p13n-sc-truncate p13n-sc-line-clamp-2')]/text()")
                if name:
                    name = name[0].get().replace("\n            ", "").replace("\n        ", "")
                if not name:
                    name = None

                price = product.xpath(".//span[@class='a-size-base a-color-price']//text()")
                if price:
                    price = price[0].get()
                else:
                    price = product.xpath(".//span[@class='p13n-sc-price']//text()")
                    if price:
                        price = price[0].get()
                    else:
                        price = None
                star_number_element = product.xpath(".//span[@class='a-icon-alt']//text()")
                if star_number_element:
                    star_number = star_number_element[0].get()
                else:
                    star_number = None
                comment_number = product.xpath(".//span[@class='a-size-small']//text()")
                if comment_number:
                    comment_number = comment_number[0].get()
                else:
                    comment_number = None
                timestamp = str(int(time.time()))

                # 数据
                product_dir = {"asin": asin, "best_sellers_rank": str(rank), "title": name, "price": price,
                               "customer_review": comment_number, "star_rating": star_number, "site": self.start_urls[0],
                               "img_url": img_url,
                               "create_time": timestamp, "category": full_cate_name}
                products_data_list.append(product_dir)
                # asin_list.append(asin)
                # yield product_dir
            except Exception as e:
                print(e)
                print(e.__traceback__.tb_lineno)
        """保存数据"""
        return products_data_list



