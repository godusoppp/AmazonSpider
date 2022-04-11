# AmazonSpider
Amazon large-scale spider

亚马逊大规模爬虫

编纂亚马逊通用的中间件与tor代理

目前支持对多个BSR站点，评论，listing商品信息，QA等进行大范围爬虫，往后会逐渐添加

scrapy框架，使用方式
scrapy crawl 运行内容 -a config_test.csv

BSR则是
scrapy crawl us_bsr -a level=3
level参数是指定层数，可在代码中配置抓取范围
