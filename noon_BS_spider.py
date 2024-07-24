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
import openpyxl
import atexit

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

def get_BS_soup(url):
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

    last_height = driver.execute_script("return document.body.scrollHeight")
    per_height = 100
    while True:
        driver.execute_script(f"window.scrollTo(0, {per_height});")
        time.sleep(10)
        per_height += 1000
        if per_height >= last_height:
            driver.execute_script(f"window.scrollTo(0, {last_height});")
            break
    # 获取整个网页的HTML代码
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    # 关闭浏览器
    driver.quit()
    return soup

def get_BS_info(categore_url):
    BSs_soup = get_BS_soup(categore_url)
    BSs = BSs_soup.find_all('span', attrs={'class': 'sc-deebe925-0 fEembb wrapper productContainer'})
    number = 1
    temp = {}
    for BS in BSs:
        if 'style' in BS.attrs:
            pass
        else:
            l1_soup = BS.find('div', attrs={'class': 'sc-19767e73-0 bwele'})
            BS_url = l1_soup.find('a')['href']
            BS_ar_url = BS_url.replace('uae-en', 'uae-ar')
            # en_title = BS_url.split('/')[4]
            img_soup = l1_soup.find_all('div', attrs={'class': 'sc-d8caf424-2 fJBKzl'})
            if img_soup:
                img_url = img_soup[0].find('img')['src']
            else:
                img_url = 'None'
            product_NO = BS_url.split('/')[3]
            title = l1_soup.find('div', attrs={'class': 'sc-ced09a79-24 cevyXQ'}).text
            price = l1_soup.find('div', attrs={'class': 'sc-8df39a2e-1 hCDaLm'}).text
            temp[number] = {'title': title, 'product_NO': product_NO, 'BS_url': base_url + BS_url, 'BS_ar_url': base_url + BS_ar_url, 'img_url': img_url, 'price': price}
        number += 1
    return temp

if __name__ == '__main__':
    base_url = 'https://www.noon.com'
    uae_url = 'https://www.noon.com/saudi-en/sa-bestsellers/'
    parameter = '?limit=100&sort%5Bby%5D=price&sort%5Bdir%5D=asc'
    
    main_page_soup = get_soup(uae_url)
    # categores_soup = main_page_soup.find('div', attrs = {'class': 'sc-6e5a97c8-2 cykjVC'})
    categores_soup = main_page_soup.find('ul', attrs = {'class': 'sc-6e5a97c8-4 gqtbgn'})
    li_elements = categores_soup.findChildren(['li'])
    categores = {}
    for i in li_elements:
        a_tag = i.find('a')
        categore_url = base_url + a_tag['href'].split('?')[0] + parameter
        categore = a_tag.text
        categores[categore] = categore_url

    print(categores)
    
    result = {}
    for categore, categore_url in categores.items():
        print(f'crawing categore: {categore}: {categore_url}')
        temp = get_BS_info(categore_url)
        if temp == {}:
            print(f'get categore: {categore}: {categore_url} failed, re-get one more time')
            temp = get_BS_info(categore_url)

        result[categore] = temp
        wait_time = random.randint(1, 5)
        time.sleep(wait_time)
    
    print('write file...')
    
    with open('saudi_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
        
    print('done')

def gen_excel(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

    # 创建一个excel写入对象
    writer = pd.ExcelWriter('saudi_result.xlsx')

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

gen_excel('saudi_result.json')