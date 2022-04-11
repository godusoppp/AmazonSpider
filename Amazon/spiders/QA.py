import scrapy
from scrapy import Request
import time
import re


class QaSpider(scrapy.Spider):
    name = 'QA'
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
        for asin_info in self.spider_asin_list:
            asin = asin_info['asin']
            site = asin_info['site']
            now_timestamp = int(time.time())
            page_url = "https://www.{}/ask/questions/inline/{}/{}?_={}".format(site, asin, 1, now_timestamp)

            yield Request(url=page_url, callback=self.handle_question_page,meta={"page":1,"site":site,"asin":asin,"times":1})

    def handle_question_page(self, response):
        # print(response.headers)
        # with open("./check.html","w",encoding="utf-8") as f:
        #     f.write(response.text)
        page = response.meta['page']
        site = response.meta['site']
        asin = response.meta['asin']
        if len(response.text) < 200:
            if page == 1:
                try_times = response.meta['times']
                if try_times >= 4:
                    return
                print("re try")
                yield Request(url=response.url, callback=self.handle_question_page,meta={"page":1,"site":site,"asin":asin,"times":try_times+1})
            return
        question_sections = response.xpath(".//div[@class='a-section askTeaserQuestions']/div")

        for question_section in question_sections:

            question = question_section.xpath(".//span[@data-action='ask-no-op']//text()")[-1].get().replace("\n",
                                                                                                            "").strip()
            first_answer = "".join(
                question_section.xpath(".//div[@class='a-fixed-left-grid-col a-col-right']/span[1]//text()").get()).replace(
                "\n",
                "").strip()
            first_answer_date = question_section.xpath(".//div[@class='a-fixed-left-grid-col a-col-right']/span[2]//text()")
            if not first_answer_date:
                first_answer_date = question_section.xpath(
                    ".//div[@class='a-section a-spacing-none a-spacing-top-micro']//text()")
            all_text = ""
            for text in first_answer_date:
                all_text += text.get()
            first_answer_date = all_text.replace("\n", "").strip().replace("              ", "").replace("           ", " ")
            question_id = question_section.xpath(".//div[@id]/@id")[0].get().replace("question-", "").replace("\n",
                                                                                                        "").strip()
            see_more_index = question_section.xpath(".//a[@class='a-link-normal askWidgetSeeAllAnswersInline']")
            if see_more_index:
                now_timestamp = int(time.time())
                api_last = re.match(".*?amazon(.*?)/",response.url).group(1)
                more_answer_url = "https://www.amazon{}/ask/answers/inline/{}/{}?_={}".format(api_last, question_id,
                                                                                              1, now_timestamp)
                yield Request(url=more_answer_url,callback=self.see_more_answer, meta={"question_id": question_id,
                                                                                       "question": question,"site":site,"asin":asin, "page": 1})
            question_info = {"question_id": question_id, "question": question, "answer": first_answer,
                             "answer_info": first_answer_date,"site":site,"asin":asin}
            # print(question_info)
            yield question_info
        now_page = re.match(".*?/(\d*?)\?_",response.url).group(1)
        next_page_url = response.url.replace("{}?_".format(now_page), "{}?_".format(int(now_page)+1))
        yield Request(url=next_page_url, callback=self.handle_question_page,meta={"page":page+1,"site":site,"asin":asin})

    def see_more_answer(self, response):
        """Request URL: https://www.amazon.com/ask/answers/inline/Tx12DBW5SA2DQA0/1?_=1640767070555
        展开回答
        """
        page = response.meta['page']
        question_id = response.meta['question_id']
        question = response.meta['question']
        site = response.meta['site']
        asin = response.meta['asin']
        answer_sections = response.xpath(".//div[@class='a-section a-spacing-none a-spacing-top-small']")
        for answer_section in answer_sections:
            answer = answer_section.xpath("./span[1]/text()")[0].get()
            other_info = answer_section.xpath(
                    ".//div[@class='a-section a-spacing-none a-spacing-top-micro']//text()")
            all_text = ""
            for text in other_info:
                all_text += text.get()
            other_info = all_text.replace("\n","").strip()
            if not other_info:
                other_info = answer_section.xpath(".//span[2]//text()")[0].get().replace("\n","").strip()
            question_info = {"question_id": question_id, "question": question,
                             "answer": answer, "answer_info": other_info,"site":site,"asin":asin}
            # print(question_info)
            yield question_info
        see_more_index = response.xpath(".//a[@class='a-link-normal askWidgetLoadMoreAnswersInline']")
        if not see_more_index:
            see_more_index = response.xpath(".//a[@class='a-link-normal askWidgetSeeRemainingAnswers']")
        if not see_more_index:
            see_more_index = response.xpath(".//a[@class='a-link-normal askWidgetSeeAllAnswersInline']")
        if see_more_index:
            next_page_url = response.url.replace("{}?_".format(page), "{}?_".format(page + 1))
            yield Request(url=next_page_url, callback=self.see_more_answer,meta={"question_id": question_id, "question": question, 'page': page+1,"site":site,"asin":asin})
