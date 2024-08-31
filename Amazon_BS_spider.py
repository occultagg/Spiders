# coding=utf-8

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

def close_file_handler():
    file_handler.close()

def get_soup(url):
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
    driver.get(url)

    # 等待页面加载
    driver.implicitly_wait(10)

    # 模拟滚动到底部
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
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

# 获取英文标题
def get_en_title(soup):
    en_bs_info = {}
    elements = soup.find_all('div', attrs={'id': 'gridItemRoot'})
    for element in elements:
        number_element = element.find('span', attrs={'class': 'zg-bdg-text'})
        try:
            number = number_element.text
        except AttributeError as e:
            logger.error(f'EN number_element crawing failed. {e}  \n crawing element: {element}')
            number = 'None'
        try:
            title_pattern = re.compile("^_cDEzb_p13n-sc-css-line-clamp.*")
            title_element = element.find('div', attrs={'class': title_pattern})
            title = title_element.text
        except AttributeError as e:
            logger.error(f'EN title_element crawing failed. {e} \n crawing element: {element}')
            title = 'None'
        en_bs_info[number] = {'title_en': title}
    return en_bs_info

# 获取分类下排名商品初步信息
def get_bs_info(base_url, categore, soup, en_soup_page):
    bs_info = {}
    # 获取英文版标题 en_bs_info = {'#1': {'title_en': 'xxxx'}}
    logger.info(f'Crawling EN title in main page: {categore}')
    en_bs_info = get_en_title(en_soup_page)
    elements = soup.find_all('div', attrs={'id': 'gridItemRoot'})
    for element in elements:
        number_element = element.find('span', attrs={'class': 'zg-bdg-text'})
        # 获取排名
        try:
            number = number_element.text
        except AttributeError as e:
            logger.error(f'number_element crawing failed. {e}  \n crawing element: {element}')
            number = 'None'
        # 获取阿拉伯文标题
        try:
            title_pattern = re.compile("^_cDEzb_p13n-sc-css-line-clamp.*")
            title_element = element.find('div', attrs={'class': title_pattern})
            title = title_element.text
        except AttributeError as e:
            logger.error(f'title_element crawing failed. {e} \n crawing element: {element}')
            title = 'None'
        # 获取阿拉伯文商品详情页url
        uri = element.find('a', attrs={'class': 'a-link-normal aok-block'}).get('href')
        url = base_url + uri
        decoded_url = unquote(url)
        # 获取Asin
        asin = decoded_url.split('/')[5]
        # 获取阿拉伯文版价格
        try:
            price_pattern = re.compile("^_cDEzb_p13n-sc-price_.*")
            price_element = element.find('span', attrs={'class': price_pattern})
            if price_element == None:
                detail_soup = get_soup(url)
                logger.info(f'Crawling in progress BS detail as can not craw price from main page: {categore}/{number} url: {url}')
                price = detail_soup.find('span', attrs={'class': 'a-offscreen'}).text
            else:
                price = price_element.text
            price_str_pattern = re.compile(r'.*ريال')
            match_test = price_str_pattern.match(price)
            if match_test:
                price = price
            else:
                price = 'None'
        except AttributeError as e:
            logger.error(f'Crawling price None both in BS detail and main page: {categore}/{number} url: {url}')
            price = 'None'
        # 获取图片url
        try:
            img_element = element.find('div', attrs={'class': 'a-section a-spacing-mini _cDEzb_noop_3Xbw5'})
            img_url = img_element.find('img')['src']
            decoded_img_url = unquote(img_url)
        except AttributeError as e:
            logger.error(f'Crawling img failed in main page: {categore}/{number} url: {url}')
            decoded_img_url = 'None'
        except TypeError as e:
            logger.error(f'Crawling img failed in main page: {categore}/{number} url: {url}. Raise ERROR: {e}')
            decoded_img_url = 'None'
        # 写入捉取的英文标题
        title_en = en_bs_info[number]['title_en']
        bs_info[number] = {'title': title, 'title_en': title_en, 'url': decoded_url, 'img_url': decoded_img_url, 'asin': asin, 'price': price}
    return bs_info

def gen_excel(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # 创建一个excel写入对象
    writer = pd.ExcelWriter('result.xlsx')

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
    

# 获取BS的price和评论
# def get_BS_detail(soup):
#     price = soup.find('span', attrs={'class': 'a-offscreen'}).text
#     comments = soup.find_all('span', attrs={'class': 'cr-original-review-content'})
#     temp = []
#     for comment in comments:
#         temp.append(comment.text)
#     comment_top_5 = [': '.join(temp[i:i+2]) for i in range(0, len(temp), 2)][:5]
#     return price, comment_top_5


if __name__ == '__main__':
    atexit.register(close_file_handler)
    try:
        # 创建日志器
        logger = logging.getLogger('my_logger')
        logger.setLevel(logging.DEBUG)

        # 创建文件处理程序
        file_handler = logging.FileHandler('logfile.log', encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # 配置日志格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # 将文件处理程序添加到日志器
        logger.addHandler(file_handler)

        # 获取类别
        base_url = 'https://www.amazon.sa'
        soup = get_soup('https://www.amazon.ae/-/en/gp/bestsellers/?ref_=nav_em_cs_bestsellers_0_1_1_2&language=ar_AE')
        categores_soup = soup.find_all('div', attrs={'role': 'treeitem'})
        categores = {}
        for categore in categores_soup[1::]:
            url = categore.find('a').get('href')
            categores[categore.text] = base_url + str(url)
        logging.debug(f'categores: {categores}')

        # print(categores)

        # 初始化json文件
        with open('result.json', 'w+', encoding='utf-8') as f:
            f.truncate(0)

        # result = {'amazon-devices' : {'#1': {'title': 'xxx', 'url': 'xxx', 'asin': 'xxx','price': 'xx', 'comments': ['comment-1', 'comment-2', ...]}}}
        result = {}

        for categore in categores.keys():
            # 按类别捉取BS前100产品
            # 阿拉伯文版url
            url_page1 = categores[categore]
            url_page2 = categores[categore] + '?pg=2'
            # 英文版url
            en_url_page1 = categores[categore] + '?language=en_AE'
            en_url_page2 = categores[categore] + '?pg=2' + '&language=en_AE'
            # 获取阿拉伯文版的soup
            logger.info(f'Crawling in progress categore: {categore} url: {url_page1}')
            soup_page1 = get_soup(url_page1)
            logger.info(f'Crawling in progress categore: {categore} url: {url_page2}')
            soup_page2 = get_soup(url_page2)
            # 获取英文版的soup
            logger.info(f'Crawling in progress categore in EN: {categore} url: {en_url_page1}')
            en_soup_page1 = get_soup(en_url_page1)
            logger.info(f'Crawling in progress categore in EN: {categore} url: {en_url_page2}')
            en_soup_page2 = get_soup(en_url_page2)
            bs_info = get_bs_info(base_url, categore, soup_page1, en_soup_page1)
            bs_info.update(get_bs_info(base_url, categore, soup_page2, en_soup_page2))
            result[categore] = bs_info
            wait_time = random.randint(1, 5)
            time.sleep(wait_time)

        with open('amazon_result_ae.json', 'a+', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        # 生成excel文件
        gen_excel('amazon_result_ae.json')

    except Exception as e:
        logger.error(f'Unexcepted ERROR: {e}')
