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
import atexit

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


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
        # 打开网页
        driver.get(url)

        # 等待页面加载
        driver.implicitly_wait(wait_time)

        # 模拟滚动到底部
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(wait_time_per_page)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # 获取整个网页的HTML代码
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        # 关闭浏览器
        driver.quit()
        return soup
    
class AmazonSpider(Spider):
    def __init__(self, language, region):
        self.language = language
        self.region = region

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
        elif self.language == 'AR':
            self.language_arg = '?language=ar_AE'
            self.title_key = 'title_ar'

    def get_categores(self, div_role='treeitem'):
        soup = self.get_soup(self.bs_url)
        categores_soup = soup.find_all('div', attrs={'role': div_role})
        categores = {}
        for categore in categores_soup[1::]:
            url = categore.find('a').get('href')
            categores[categore.text] = self.base_url + str(url)

        self.categores = categores

    def get_bs_title(self, bs_list_url, titles_div_id='gridItemRoot', title_span_class='zg-bdg-text'):
        bs_title_info = {}
        soup = self.get_soup(bs_list_url)
        elements = self.soup.find_all('div', attrs={'id': titles_div_id})
        for element in elements:
            number_element = element.find('span', attrs={'class': title_span_class})
            try:
                number = number_element.text
            except AttributeError as e:
                number = 'None'
            try:
                title_pattern = re.compile("^_cDEzb_p13n-sc-css-line-clamp.*")
                title_element = element.find('div', attrs={'class': title_pattern})
                title = title_element.text
            except AttributeError as e:
                title = 'None'
            bs_title_info[number] = {self.title_key: title}
        return bs_title_info
    
    def get_bs_info(self, categore, bs_elements_div_id='gridItemRoot', number_span_class='zg-bdg-text', bs_detail_url_a_class='a-link-normal aok-block',
                    price_pattern_re='^_cDEzb_p13n-sc-price_.*', img_div_class='a-section a-spacing-mini _cDEzb_noop_3Xbw5'
                    ):
        bs_info = {}
        soup = self.get_soup()
        # 获取页面所有bs的元素
        bs_elements = soup.find_all('div', attrs={'id': bs_elements_div_id})
        for element in bs_elements:
            number_element = element.find('span', attrs={'class': number_span_class})
            # 获取排名
            try:
                number = number_element.text
            except AttributeError as e:
                self.logger.error(f'number_element crawing failed. {e}  \n crawing element: {element}')
                number = 'None'
            # 获取阿拉伯文标题
            # try:
            #     title_pattern = re.compile(title_pattern_re)
            #     title_element = element.find('div', attrs={'class': title_pattern})
            #     title = title_element.text
            # except AttributeError as e:
            #     self.logger.error(f'title_element crawing failed. {e} \n crawing element: {element}')
            #     title = 'None'
            # 获取商品详情页url
            uri = element.find('a', attrs={'class': bs_detail_url_a_class}).get('href')
            url = self.base_url + uri
            decoded_url = unquote(url)
            # 获取Asin
            asin = decoded_url.split('/')[5]
            # 获取价格
            try:
                price_pattern = re.compile(price_pattern_re)
                price_element = element.find('span', attrs={'class': price_pattern})
                if price_element == None:
                    detail_soup = self.get_soup(url)
                    self.logger.info(f'Crawling in progress BS detail as can not craw price from main page: {categore}/{number} url: {url}')
                    price = detail_soup.find('span', attrs={'class': 'a-offscreen'}).text
                else:
                    price = price_element.text
                # 检查获取到的price
                price_str_pattern = re.compile(r'.*ريال')
                match_test = price_str_pattern.match(price)
                if not match_test:
                    price = 'None'
            except AttributeError as e:
                self.logger.error(f'Crawling price None both in BS detail and main page: {categore}/{number} url: {url}')
                price = 'None'
            # 获取图片url
            try:
                img_element = element.find('div', attrs={'class': img_div_class})
                img_url = img_element.find('img')['src']
                decoded_img_url = unquote(img_url)
            except AttributeError as e:
                self.logger.error(f'Crawling img failed in main page: {categore}/{number} url: {url}')
                decoded_img_url = 'None'
            except TypeError as e:
                self.logger.error(f'Crawling img failed in main page: {categore}/{number} url: {url}. Raise ERROR: {e}')
                decoded_img_url = 'None'

            bs_info[categore] = number
            bs_info[categore][number] = {'url': decoded_url, 'img_url': decoded_img_url, 'asin': asin, 'price': price}
        self.bs_info = bs_info
        return bs_info