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

class AmazonSpider:
    def __init__(self, base_url, url, headless=True, no_gpu=True):
        self.headless = headless
        self.no_gpu = no_gpu
        self.base_url = base_url
        self.url = url
        self.init_driver()
        self.get_soup()
        
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

    def get_soup(self, wait_time=10, wait_time_per_page=5):
        driver = self.driver
        # 打开网页
        driver.get(self.url)

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

    def get_categores(self, div_role='treeitem'):
        categores_soup = self.soup.find_all('div', attrs={'role': div_role})
        categores = {}
        for categore in categores_soup[1::]:
            url = categore.find('a').get('href')
            categores[categore.text] = self.base_url + str(url)

        self.categores = categores

    def get_bs_title(self, title_key, titles_div_id='gridItemRoot', title_span_class='zg-bdg-text'):
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
            bs_title_info[number] = {title_key: title}
        return bs_title_info
    
    def get_price_from_detail(self, price_span_class='a-offscreen'):
        detail_soup = self.soup
        try:
            price = detail_soup.find(
            'span', attrs={'class': price_span_class}).text
        except AttributeError as e:
            price = 'None'

        # 检查获取到的price
        # price_str_pattern = re.compile(r'.*ريال')
        # match_test = price_str_pattern.match(price)
        # if not match_test:
        #     price = 'None'

        return price
    
    def get_bs_info(self, region, categore, bs_elements_div_id='gridItemRoot', number_span_class='zg-bdg-text', bs_detail_url_a_class='a-link-normal aok-block', price_pattern_re='^_cDEzb_p13n-sc-price_.*', img_div_class='a-section a-spacing-mini _cDEzb_noop_3Xbw5'
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
                number = 'None'
            # 获取商品详情页url
            try:
                uri = element.find(
                    'a', attrs={'class': bs_detail_url_a_class}).get('href')
            except AttributeError as e:
                uri = None
            detail_url = self.base_url + uri
            decoded_url = unquote(detail_url)
            # 获取Asin
            if region == 'sa':
                asin = decoded_url.split('/')[7]
            elif region == 'ae':
                asin = decoded_url.split('/')[5]
            # 获取价格
            try:
                price_pattern = re.compile(price_pattern_re)
                price_element = element.find(
                    'span', attrs={'class': price_pattern})
                if price_element == None:
                    price = 'None'
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
                decoded_img_url = 'None'
            except TypeError as e:
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
        with open('' + self.json_filename, 'w', encoding='utf-8') as f:
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

def get_titles(categore, categore_url, base_url, region, retry):
    titles_en_1, titles_en_2, titles_ar_1, titles_ar_2 = {}, {}, {}, {}
    for i in range(retry):
        # EN page 1
        categore_en_obj_1 = AmazonSpider(url=categore_url, base_url=base_url)
        # EN title
        titles_en_1 = categore_en_obj_1.get_bs_title(title_key='title_en')
        if not titles_en_1 == {}:
            break
        else:
            random_wait = random.randint(5, 15)
            print(f'get titles_en_1 failed, wait {random_wait}s and re-try. {i}')
            time.sleep(random_wait)
    
    for i in range(retry):
        # AR page 1
        categore_ar_obj_1 = AmazonSpider(url=categore_url + '?language=ar_AE', base_url=base_url)
        # AR title
        titles_ar_1 = categore_ar_obj_1.get_bs_title(title_key='title_ar')
        if not titles_ar_1 == {}:
            break
        else:
            random_wait = random.randint(5, 15)
            print(f'get titles_ar_1 failed, wait {random_wait}s and re-try. {i} URL: {categore_url}')
            time.sleep(random_wait)
    
    for i in range(retry):
        # EN page 2
        categore_en_obj_2 = AmazonSpider(url=categore_url + '?ie=UTF8&pg=2', base_url=base_url)
        # EN title
        titles_en_2 = categore_en_obj_2.get_bs_title(title_key='title_en')
        if not titles_en_2 == {}:
            break
        else:
            random_wait = random.randint(5, 15)
            print(f'get titles_en_2 failed, wait {random_wait}s and re-try. {i}  URL: {categore_url}')
            time.sleep(random_wait)

    for i in range(retry):
        # AR page 2
        categore_ar_obj_2 = AmazonSpider(url=categore_url + '?ie=UTF8&pg=2' + '&language=ar_AE', base_url=base_url)
        # AR title
        titles_ar_2 = categore_ar_obj_2.get_bs_title(title_key='title_ar')
        if not titles_ar_2 == {}:
            break
        else:
            random_wait = random.randint(5, 15)
            print(f'get titles_ar_2 failed, wait {random_wait}s and re-try. {i}  URL: {categore_url}')
            time.sleep(random_wait)

    # merge
    titles_en = { **titles_en_1, **titles_en_2 }
    titles_ar = { **titles_ar_1, **titles_ar_2 }
    for num in titles_en.keys():
        titles_en[num].update(titles_ar[num])
    titles = titles_en
    pickling = GenExecl(data=titles, json_filename=f'./json_files/{categore}_titles_{region}.json', result_filename=None)
    pickling.pickling()
    return titles, categore_en_obj_1, categore_en_obj_2, categore_ar_obj_1, categore_ar_obj_2

def main(base_url, bs_url, json_filename, result_filename, region, retry):
    # SA
    sa = AmazonSpider(url=bs_url, base_url=base_url)
    sa.get_categores()
    result = {}
    for categore, categore_url in sa.categores.items():
        titles, categore_en_obj_1, categore_en_obj_2, _, _ = get_titles(categore=categore, categore_url=categore_url, base_url=base_url, region=region, retry=retry)
        bs_info_1 = categore_en_obj_1.get_bs_info(categore=categore, region=region)
        bs_info_2 = categore_en_obj_2.get_bs_info(categore=categore, region=region)
        bs_info_1[categore].update(bs_info_2[categore])
        bs_info = bs_info_1
        # check price
        for num in bs_info[categore].keys():
            if bs_info[categore][num]['price'] == 'None':
                detail = AmazonSpider(url=bs_info[categore][num]['detail_url'], base_url=base_url)
                bs_info[categore][num]['price'] = detail.get_price_from_detail()
                random_wait = random.randint(5, 15)
                time.sleep(random_wait)
        # merge title and bs info
        for num in titles.keys():
            bs_info[categore][num].update(titles[num])
        result.update(bs_info)
        random_wait = random.randint(5, 15)
        time.sleep(random_wait)

    pickling = GenExecl(data=result, json_filename=json_filename, result_filename=result_filename)
    pickling.pickling()
    pickling.gen_execl()

if __name__ == '__main__':
    # SA
    main(base_url='https://www.amazon.sa', bs_url='https://www.amazon.sa/-/en/gp/bestsellers', json_filename='./json_files/amazon_bs_sa.json', result_filename='amazon_bs_sa.xlsx', region='sa', retry=5)

    random_wait = random.randint(5, 15)
    time.sleep(random_wait)

    # UAE
    main(base_url='https://www.amazon.ae', bs_url='https://www.amazon.ae/-/en/gp/bestsellers', json_filename='./json_files/amazon_bs_ae.json', result_filename='amazon_bs_ae.xlsx', region='ae', retry=5)

