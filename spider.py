#! coding=utf-8

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import unquote
import time
import random
import json
import logging
import re
import pandas as pd

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class Spider:
    def __init__(self, headless, no_gpu):
        self.headless = headless
        self.no_gpu = no_gpu
        self.logger = logging.getLogger(self.__class__.__name__)

    def init_driver(self):
        if self.headless:
            head_arg = '--headless'
        if self.no_gpu:
            gpu_arg = '--disable-gpu'
        # 初始化Chrome浏览器选项
        chrome_options = webdriver.ChromeOptions()
        # 设置无头模式
        chrome_options.add_argument(head_arg)
        # 额外的设置，例如禁用GPU加速，当你在没有显示器的服务器上运行时可能需要
        chrome_options.add_argument(gpu_arg)

        # 使用更新的Service类和ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver = driver

    def get_soup(self, url, wait_time=10, wait_time_per_page=5):
        driver = self.driver
        self.url = url
        # 打开网页
        driver.get(url)

        # 等待页面加载
        driver.implicitly_wait(wait_time)

        # 模拟滚动到底部
        last_height = driver.execute_script(
            "return document.body.scrollHeight")
        while True:
            driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(wait_time_per_page)
            new_height = driver.execute_script(
                "return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # 获取整个网页的HTML代码
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        # 关闭浏览器
        driver.quit()
        self.soup = soup


class AmazonSpider(Spider):
    def __init__(self, headless, no_gpu, language, region, page2=False):
        super().__init__(headless, no_gpu)
        self.language = language
        self.region = region
        self.page2 = page2
        self.init_driver()
        self.set_language()

    def set_language(self):
        if self.region == 'SA':
            self.base_url = 'https://www.amazon.sa'
            self.bs_url = 'https://www.amazon.sa/-/en/gp/bestsellers/'
        elif self.region == 'UAE':
            self.base_url = 'https://www.amazon.ae'
            self.bs_url = 'https://www.amazon.ae/-/en/gp/bestsellers/'

        if self.language == 'EN':
            self.language_arg = '?language=en_AE'
            self.title_key = 'title_en'
            if self.page2:
                self.language_arg = '&language=en_AE'
        elif self.language == 'AR':
            self.language_arg = '?language=ar_AE'
            self.title_key = 'title_ar'
            if self.page2:
                self.language_arg = '&language=ar_AE'

    def get_categores(self, div_role='treeitem'):
        self.logger.info(
            f'crawing categores page: {self.bs_url}, url: {self.url}')
        soup = self.soup
        categores_soup = soup.find_all('div', attrs={'role': div_role})
        categores = {}
        for categore in categores_soup[1::]:
            url = categore.find('a').get('href')
            categores[categore.text] = self.base_url + str(url)

        self.categores = categores

    def get_bs_title(self, titles_div_id='gridItemRoot', title_span_class='zg-bdg-text'):
        self.logger.info(
            f'crawing BS title in language: {self.language}, url: {self.url}')
        bs_title_info = {}
        soup = self.soup
        elements = soup.find_all('div', attrs={'id': titles_div_id})
        for element in elements:
            number_element = element.find(
                'span', attrs={'class': title_span_class})
            try:
                number = number_element.text
            except AttributeError as e:
                number = 'None'
            try:
                title_pattern = re.compile("^_cDEzb_p13n-sc-css-line-clamp.*")
                title_element = element.find(
                    'div', attrs={'class': title_pattern})
                title = title_element.text
            except AttributeError as e:
                title = 'None'
            bs_title_info[number] = {self.title_key: title}
        return bs_title_info

    def get_price_from_detail(self, detail_url, price_span_class='a-offscreen'):
        self.logger.info(
            f'crawing price from detail page: {self.language}, url: {detail_url}')
        detail_soup = self.soup
        price = detail_soup.find(
            'span', attrs={'class': price_span_class}).text

        # 检查获取到的price
        price_str_pattern = re.compile(r'.*ريال')
        match_test = price_str_pattern.match(price)
        if not match_test:
            price = 'None'

        return price

    def get_bs_info(self, categore, bs_elements_div_id='gridItemRoot', number_span_class='zg-bdg-text', bs_detail_url_a_class='a-link-normal aok-block', price_pattern_re='^_cDEzb_p13n-sc-price_.*', img_div_class='a-section a-spacing-mini _cDEzb_noop_3Xbw5'
                    ):
        bs_info = {}
        bs_info[categore] = {}
        soup = self.soup
        # 获取页面所有bs的元素
        bs_elements = soup.find_all('div', attrs={'id': bs_elements_div_id})
        for element in bs_elements:
            number_element = element.find(
                'span', attrs={'class': number_span_class})
            # 获取排名
            try:
                number = number_element.text
            except AttributeError as e:
                self.logger.error(
                    f'number_element crawing failed. {e}  \n crawing element: {element}')
                number = 'None'
            # 获取商品详情页url
            uri = element.find(
                'a', attrs={'class': bs_detail_url_a_class}).get('href')
            detail_url = self.base_url + uri
            decoded_url = unquote(detail_url)
            # 获取Asin
            asin = decoded_url.split('/')[7]
            # 获取价格
            try:
                price_pattern = re.compile(price_pattern_re)
                price_element = element.find(
                    'span', attrs={'class': price_pattern})
                if price_element == None:
                    detail = AmazonSpider(
                        headless=self.headless, no_gpu=self.no_gpu, region=self.region, language=self.language)
                    detail.get_soup(url=detail_url + self.language_arg)
                    price = detail.get_price_from_detail(detail_url=detail_url)
                else:
                    price = price_element.text
            except AttributeError as e:
                price = 'None'
            # 获取图片url
            try:
                img_element = element.find(
                    'div', attrs={'class': img_div_class})
                img_url = img_element.find('img')['src']
                decoded_img_url = unquote(img_url)
            except AttributeError as e:
                self.logger.error(
                    f'Crawling img failed in main page: {categore}/{number} url: {self.url}')
                decoded_img_url = 'None'
            except TypeError as e:
                self.logger.error(
                    f'Crawling img failed in main page: {categore}/{number} url: {self.url}. Raise ERROR: {e}')
                decoded_img_url = 'None'
            bs_info[categore][number] = {
                'detail_url': decoded_url, 'img_url': decoded_img_url, 'asin': asin, 'price': price}
        self.bs_info = bs_info
        return bs_info


class GenExecl:
    def __init__(self, json_filename, result_filename, data):
        self.json_filename = json_filename
        self.data = data
        self.result_filename = result_filename

    def pickling(self):
        with open(self.json_filename, 'w', encoding='utf-8') as f:
            json_str = json.dump(self.data, f)

    def gen_execl(self):
        with open(self.json_filename, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # 创建一个excel写入对象
        writer = pd.ExcelWriter(self.result_filename)

        for categore, items in json_data.items():
            data = []
            for index, item_detail in items.items():
                item_detail['number'] = index
                data.append(item_detail)
            df = pd.DataFrame(data)
            cols = df.columns.tolist()
            cols = ['number'] + [col for col in cols if col != 'number']
            df = df[cols]
            df.to_excel(writer, sheet_name=categore, index=False)

        writer._save()


if __name__ == '__main__':
    def crawing_amazon(region):
        result = {}
        # crawing AWS SA BS site
        aws_spider = AmazonSpider(
            headless=True, no_gpu=True, region=region, language='EN')
        aws_spider.get_soup(url=aws_spider.bs_url + aws_spider.language_arg)
        aws_spider.get_categores()
        for categore, categore_url in aws_spider.categores.items():
            titles_en = {}
            titles_ar = {}
            titles_en_2 = {}
            titles_ar_2 = {}
            result = {}
            while titles_en == {}:
                # en title
                aws_bs_spider_en = AmazonSpider(
                    headless=True, no_gpu=True, region=region, language='EN')
                aws_bs_spider_en.get_soup(
                    url=categore_url + aws_bs_spider_en.language_arg)
                titles_en = aws_bs_spider_en.get_bs_title()

                sleep_time = random.randint(5, 10)
                time.sleep(sleep_time)

            while titles_ar == {}:
                # ar title
                aws_bs_spider_ar = AmazonSpider(
                    headless=True, no_gpu=True, region=region, language='AR')
                aws_bs_spider_ar.get_soup(
                    url=categore_url + aws_bs_spider_ar.language_arg)
                titles_ar = aws_bs_spider_ar.get_bs_title()

                sleep_time = random.randint(5, 10)
                time.sleep(sleep_time)

            bs_info = aws_bs_spider_en.get_bs_info(categore=categore)
            for num in bs_info[categore].keys():
                title_key_en = aws_bs_spider_en.title_key
                bs_info[categore][num][title_key_en] = titles_en[num][title_key_en]
                title_key_ar = aws_bs_spider_ar.title_key
                bs_info[categore][num][title_key_ar] = titles_ar[num][title_key_ar]

            sleep_time = random.randint(5, 10)
            time.sleep(sleep_time)

            # page 2
            categore_url_2 = categore_url + '?ie=UTF8&pg=2'
            while titles_en_2 == {}:
                # en title
                aws_bs_spider_en_2 = AmazonSpider(
                    headless=True, no_gpu=True, region=region, language='EN', page2=True)
                aws_bs_spider_en_2.get_soup(
                    url=categore_url_2 + aws_bs_spider_en_2.language_arg)
                titles_en_2 = aws_bs_spider_en_2.get_bs_title()

                sleep_time = random.randint(5, 10)
                time.sleep(sleep_time)

            while titles_ar_2 == {}:
                # ar title
                aws_bs_spider_ar_2 = AmazonSpider(
                    headless=True, no_gpu=True, region=region, language='AR', page2=True)
                aws_bs_spider_ar_2.get_soup(
                    url=categore_url_2 + aws_bs_spider_ar_2.language_arg)
                titles_ar_2 = aws_bs_spider_ar_2.get_bs_title()

                sleep_time = random.randint(5, 10)
                time.sleep(sleep_time)

            bs_info_2 = aws_bs_spider_en_2.get_bs_info(categore=categore)
            for num in bs_info_2[categore].keys():
                title_key_en = aws_bs_spider_en_2.title_key
                bs_info_2[categore][num][title_key_en] = titles_en_2[num][title_key_en]
                title_key_ar = aws_bs_spider_ar_2.title_key
                bs_info_2[categore][num][title_key_ar] = titles_ar_2[num][title_key_ar]

            bs_info[categore].update(bs_info_2[categore])
            result.update(bs_info)

        return result

    result = crawing_amazon(region='SA')
    g = GenExecl(data=result, json_filename='amazon_bs_sa.json',
                 result_filename='amazon_bs_sa.xlsx')
    g.pickling()
    g.gen_execl()

    # sleep_time = random.randint(30,60)
    # time.sleep(sleep_time)
    # crawing_amazon(region='UAE', json_filename='amazon_bs_uae.json',
    #                result_filename='amazon_bs_uae.xlsx')
