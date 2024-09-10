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

class NoonSpider:
    def __init__(self, base_url, url, parameter, headless=True, no_gpu=True):
        self.headless = headless
        self.no_gpu = no_gpu
        self.base_url = base_url
        self.parameter = parameter
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

    def get_soup(self, wait_time=10):
        # 初始化Chrome浏览器选项
        chrome_options = webdriver.ChromeOptions()

        # 设置无头模式
        chrome_options.add_argument("--headless")
        # 额外的设置，例如禁用GPU加速，当你在没有显示器的服务器上运行时可能需要
        chrome_options.add_argument("--disable-gpu")

        # 使用更新的Service类和ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        # 打开网页
        driver.get(self.url)
        # 等待页面加载
        driver.implicitly_wait(wait_time)

        last_height = driver.execute_script("return document.body.scrollHeight")
        per_height = 100
        while True:
            driver.execute_script(f"window.scrollTo(0, {per_height});")
            time.sleep(wait_time)
            per_height += 1000
            if per_height >= last_height:
                driver.execute_script(f"window.scrollTo(0, {last_height});")
                break
        # 获取整个网页的HTML代码
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        # 关闭浏览器
        driver.quit()
        self.soup = soup

    def get_categores(self, ur_class='sc-6e5a97c8-4 gqtbgn'):
        categores_soup = self.soup.find('ul', attrs = {'class': ur_class})
        li_elements = categores_soup.findChildren(['li'])
        categores = {}
        for i in li_elements:
            a_tag = i.find('a').get('href').split('?')[0]
            categore_url = self.base_url + a_tag + self.parameter
            categore = i.find('a').text
            categores[categore] = categore_url

        self.categores = categores
    
    # bss_span_class='sc-c25694a3-0 iLpufk wrapper productContainer'
    def get_bs_info(self):
        bs_info = {}
        bss_pattern = re.compile(".*wrapper productContainer")
        bss = self.soup.find_all('span', attrs={'class': bss_pattern})
        number = 1
        for bs in bss:
            if 'style' in bs.attrs:
                pass
            else:
                l1_soup = bs.find('div', attrs={'class': 'sc-19767e73-0 bwele'})
                bs_url = l1_soup.find('a')['href']
                bs_ar_url = bs_url.replace('uae-en', 'uae-ar')
                img_soup = l1_soup.find_all('div', attrs={'class': 'sc-d8caf424-2 fJBKzl'})
                if img_soup:
                    img_url = img_soup[0].find('img')['src']
                else:
                    img_url = 'None'
                product_NO = bs_url.split('/')[3]
                title = l1_soup.find('div', attrs={'class': 'sc-26c8c6bb-24 cCbHzm'}).text
                price = l1_soup.find('div', attrs={'class': 'sc-8df39a2e-1 hCDaLm'}).text
                bs_info[number] = {'title': title, 'product_NO': product_NO, 'BS_url': self.base_url + bs_url, 'bs_ar_url': self.base_url + bs_ar_url, 'img_url': img_url, 'price': price}
            number += 1
        return bs_info
    
class GenExecl:
    def __init__(self, json_filename, result_filename, data):
        self.json_filename = json_filename
        self.data = data
        self.result_filename = result_filename

    def pickling(self):
        with open(self.json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)

    def gen_excel(self):
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

def main(base_url, url, parameter, json_filename, region, result_filename, type):
    spider = NoonSpider(base_url, url, parameter=parameter)
    spider.get_categores()
    result = {}
    for categore, categore_url in spider.categores.items():
        bs_info = {}
        categore_obj = NoonSpider(base_url=base_url, url=categore_url, parameter=parameter)
        bs_info[categore] = categore_obj.get_bs_info()
        result.update(bs_info)
        pickling = GenExecl(data=bs_info, json_filename=f'json_files/noon_{type}_{categore}_{region}.json' , result_filename=None)
        pickling.pickling()
        random_wait = random.randint(5, 15)
        time.sleep(random_wait)

    pickling = GenExecl(data=result, json_filename=json_filename, result_filename=result_filename)
    pickling.pickling()
    pickling.gen_excel()

if __name__ == '__main__':
    # UAE BS
    main(base_url='https://www.noon.com', url='https://www.noon.com/uae-en/ae-bestsellers/', region='uae', json_filename='json_files/noon_bs_uae.json', result_filename='result/noon_bs_uae.xlsx', parameter='?limit=100&sort%5Bby%5D=price&sort%5Bdir%5D=asc', type='bs')
    # UAE new
    # main(base_url='https://www.noon.com', url='https://www.noon.com/uae-en/ae-bestsellers/', region='uae', json_filename='json_files/noon_new_uae.json', result_filename='result/noon_new_uae.xlsx', parameter='?limit=100&sort%5Bby%5D=new_arrivals&sort%5Bdir%5D=desc', type='new')
