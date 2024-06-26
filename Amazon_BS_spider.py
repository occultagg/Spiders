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

def get_soup(driver, url):
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
    clean_html = html.replace('u200e', '')
    soup = BeautifulSoup(clean_html, 'html.parser')

    # 关闭浏览器
    driver.quit()
    return soup

# 获取分类下排名商品初步信息
def get_bs_info(base_url, soup):
    bs_info = {}
    elements = soup.find_all('div', attrs={'id': 'gridItemRoot'})
    for element in elements:
            number_element = element.find('span', attrs={'class': 'zg-bdg-text'})
            try:
                number = number_element.text
            except AttributeError as e:
                logging.error(f'number_element crawing failed. {e}  \n crawing element: {element}')
                number = 'None'
            try:
                pattern = re.compile("^_cDEzb_p13n-sc-css-line-clamp.*")
                title_element = element.find('div', attrs={'class': pattern})
                title = title_element.text
            except AttributeError as e:
                logging.error(f'title_element crawing failed. {e} \n crawing element: {element}')
                title = 'None'
            uri = element.find('a', attrs={'class': 'a-link-normal aok-block'}).get('href')
            url = base_url + uri
            decoded_url = unquote(url)
            asin = decoded_url.split('/')[7]
            bs_info[number] = {'title': title, 'url': decoded_url, 'asin': asin}
    return bs_info

# 获取BS的price和评论
def get_BS_detail(soup):
    price = soup.find('span', attrs={'class': 'a-offscreen'}).text
    comments = soup.find_all('span', attrs={'class': 'cr-original-review-content'})
    temp = []
    for comment in comments:
        temp.append(comment.text)
    comment_top_5 = [': '.join(temp[i:i+2]) for i in range(0, len(temp), 2)][:5]
    return price, comment_top_5


if __name__ == '__main__':
    # 配置根日志器的日志级别和输出格式
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

    # 创建一个文件处理器，将日志信息写入到指定文件路径
    file_handler = logging.FileHandler('logfile.log', encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # 定义日志文件的输出格式, 可根据需要自定义
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # 获取根日志器，并将文件处理器添加到根日志器中
    logger = logging.getLogger()
    logger.addHandler(file_handler)

    # 初始化Chrome浏览器选项
    chrome_options = webdriver.ChromeOptions()
    # 设置无头模式
    chrome_options.add_argument("--headless")
    # 额外的设置，例如禁用GPU加速，当你在没有显示器的服务器上运行时可能需要
    chrome_options.add_argument("--disable-gpu")

    # 使用更新的Service类和ChromeDriverManager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # 获取类别
    base_url = 'https://www.amazon.sa'
    soup = get_soup(driver, 'https://www.amazon.sa/-/en/gp/bestsellers/?ref_=nav_em_cs_bestsellers_0_1_1_2&language=ar_AE')
    categores_soup = soup.find_all('div', attrs={'role': 'treeitem'})
    categores = {}
    for categore in categores_soup[1::]:
        url = categore.find('a').get('href')
        categores[categore.text] = base_url + str(url) 

    # 初始化json文件
    with open('result.json', 'r+', encoding='utf-8') as f:
        f.truncate(0)

    # result = {'amazon-devices' : {'#1': {'title': 'xxx', 'url': 'xxx', 'price': 'xx', 'comments': ['comment-1', 'comment-2', ...]}}}
    result = {}

    for categore in categores.keys():
        # 按类别捉取BS前100产品
        url_page1 = categores[categore]
        url_page2 = categores[categore] + '?pg=2'
        logging.info(f'Crawling in progress categore: {categore} url: {url_page1}')
        soup_page1 = get_soup(driver, url_page1)
        logging.info(f'Crawling in progress categore: {categore} url: {url_page2}')
        soup_page2 = get_soup(driver, url_page2)
        bs_info = get_bs_info(base_url, soup_page1)
        bs_info.update(get_bs_info(base_url, soup_page2))
        result[categore] = bs_info
        # 捉取price和comment
        for BS_number in result[categore].keys():
            BS_detail_url = result[categore][BS_number]['url']
            soup_detail = get_soup(driver, BS_detail_url)
            logging.info(f'Crawling in progress BS detail: {categore}/{BS_number} url: {BS_detail_url}')
            price, comment_top_5 = get_BS_detail(soup_detail)
            result[categore][BS_number]['price'] = price
            result[categore][BS_number]['comments'] = comment_top_5
            # 随机等待1-5s
            wait_time = random.randint(1, 5)
            time.sleep(wait_time)

    with open('result.json', 'a+', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    # 关闭文件处理器（可选，根据需求决定是否关闭）
    file_handler.close()