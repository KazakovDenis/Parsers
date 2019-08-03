""" Скрипт извлекает из сайта поставщика артикулы, ссылки на изображения и описания товаров:
- находим в каталоге ссылки на страницы категорий товаров
- заходим в категорию, парсим товары
- находим пагинацию, переходим на следующую страницу
- если последняя страница / нет товаров переходим в следующую категорию """
# lxml не используется, но без неё скрипт не работает

# добавил счётчик спарсенных категорий

# todo заменить переход по пагинации на переход по &page
# todo сделать генератор прокси/ua с yield
# todo сделать запись непарсенных страниц


import requests
import csv
import certifi
import lxml
from bs4 import BeautifulSoup
from datetime import datetime
from multiprocessing import Pool
from random import choice, uniform
from time import sleep


# страница входа 
url = 'https://uniqom.ru/catalog'
# маскируемся: исходные данные для requests.get
default_agent = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                               'Chrome/75.0.3770.142 Safari/537.36'}
default_proxy = {'http': 'http://41.89.171.220:8080', 'https': 'http://41.89.171.220:8080'}


def get_response(url, useragent=default_agent, proxy=default_proxy):
    """ Получаем ответ страницы по урл с паузой.
    Ожидаемый возврат - <Response 200>"""
    print('Trying to parse', url)
    timeout = uniform(35, 40)
    try:
        response = requests.get(url, headers=useragent, proxies=proxy, timeout=timeout, verify=certifi.where())
        # делаем паузу
        pause = uniform(3, 6)
        sleep(pause)
        return response
    # в случае бана меняем на случайные прокси и юзер-агент
    except requests.exceptions.RequestException as e:
        print(f'Error for {url}. More info:', e)
        useragent = {'User-Agent': choice(useragents_list)}
        proxy = {'http': choice(proxy_list), 'https': choice(proxy_list)}
        # пробуем снова с бОльшей паузой
        pause = uniform(10, 15)
        sleep(pause)
        get_response(url, useragent, proxy)
    except Exception as e:
        # непредусмотренные ошибки
        print(f'Another Error for {url} in get_response():', e)


def get_category_links(dom):
    """ Находим на странице входа ссылки на страницы для парсинга и выдаёт в виде списка.
     Ожидаемый возврат - список со ссылками """
    soup = BeautifulSoup(dom, 'lxml')
    # получаем все теги <li> на странице с указанным классом
    lis = soup.find_all('li', class_='feip-productsList-level4-label')
    links = []
    for li in lis:
        # получаем атрибут href тега <a>, находящегося внутри каждого <li>
        a = li.find('a').get('href')
        link = 'https://uniqom.ru' + a
        links.append(link)
    return links


def write_csv(data):
    """ Записываем данные в csv """
    with open('uniqom.csv', 'a', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=';')
        writer.writerow(data)


def get_category_data(response):
    """ Парсим страницы категории товаров и пишем в csv """
    try:
        soup = BeautifulSoup(response.text, 'lxml')
        # извлекаем список товаров на странице, проходим по списку
        goods_rows = soup.find_all('div', class_='feip-productsList-product-row')
        for each in goods_rows:
            # извлекаем артикул
            try:
                articul = each.find('div', class_='feip-productsList-product-articleID').text.strip()
            except:
                articul = 'articul exception'
            # извлекаем изображение
            try:
                image = 'https:' + each.find('div', class_='feip-productsList-photoCell').find('a').get('href')
                if 'bw-logotype.png' in image:
                    image = 'no img'
            except:
                image = 'img exception'
            # извлекаем описание
            try:
                description = each.find('div', class_='feip-productsList-'
                                                      'product-variationLine').find('div').text.strip()
            except:
                description = 'description exception'
            # сохраняем в data, data пишем в csv
            data = [articul, image, description]
            write_csv(data)
            # ---------- конец тела цикла извлечения параметров товаров
        print(f'Page "{response.url}" has been parsed')
        # ищем пагинацию и переходим по ней
        follow_next_page(soup)
    except:
        print(f'No data here {response.url}')


def follow_next_page(soup):
    """ Переходим на следующую страницу внутри категории товаров """
    try:
        pagination = soup.find('li', class_='uk-pagination-next').find('a').get('href')
        next_page = 'https://uniqom.ru' + pagination
        parse_pages(next_page)
        # далее - перебор страниц через &page
        # url ? вынести функцию из get_page_data ?
        # last_page = int(soup.find('ul', class_='uk-pagination').find_all('li')[-2].find('a').text.strip())
        # number = 1
        # while number <= last_page:
        #     next_page = url + '&page=' + str(i)
        #     parse_pages(next_page)
        #     number += 1
    except:
        # если не найдена ссылка на следующую страницу, значит парсинг категории окончен
        title = soup.find('title').text.strip()
        parsed_category_counter += 1
        percent = round(parsed_category_counter / 271, 1)
        print(f'"{title}" has been parsed./n Progress: {parsed_category_counter} / 271 ({percent}%)')


# пишем функцию для параллельного парсинга
def parse_pages(url):
    # оставляем только локальные склады
    if 'deposits=2' not in url:
        url += '?&deposits=2&limit=100'
    # входим на страницу и парсим её
    try:
        response = get_response(url)
        assert response is not None, f'{url} is returned as None'
        if response.status_code == 200:
            get_category_data(response)
        else:
            print(f'Status {response.status_code} of page {url}')
    except AssertionError as a:
        print(a)
    except Exception as e:
        print(f'Another trouble with {url}:', e)


def time_decorator(func):
    """ Декоратор считает время выполнения всего скрипта """
    def wrapper():
        # начинаем отсчёт времени работы модуля
        start = datetime.now()
        print(f'Parsing started at {start}')
        func()
        # считаем и выводим затраченное время
        period = datetime.now() - start
        print('Time wasted: ', str(period))
    return wrapper


@time_decorator
def main():
    # глобально объявляем данные, необходимые для избежания бана
    global parsed_category_counter, useragents_list, proxy_list
    parsed_category_counter = 0

    # получаем список юзер-агентов из файла
    with open("useragents.txt", "r") as useragents_file:
        useragents_list = useragents_file.read().split('\n')

    # получаем список прокси из файла (прокси проверять отдельно!)
    with open("proxylist.txt", "r") as proxy_file:
        proxy_list = proxy_file.read().split('\n')

    # получаем на странице входа список ссылок на страницы категорий
    index = get_response(url).text
    assert index is not None, 'Главна страница не отвечает'
    category_links = get_category_links(index)   # 271 категория

    # код для парсинга N параллельными процессами
    with Pool(2) as p:
        p.map(parse_pages, category_links)


if __name__ == '__main__':
    main()
