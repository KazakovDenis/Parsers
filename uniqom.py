""" Скрипт извлекает из сайта поставщика артикулы, ссылки на изображения и описания товаров:
- находим в каталоге ссылки на страницы категорий товаров
- заходим в категорию, парсим товары
- находим пагинацию, переходим на следующую страницу
- если последняя страница / нет товаров переходим в следующую категорию """
# lxml не используется, но без неё скрипт не работает

# заменил переход по пагинации на переход по &page
# понял что choice актуальнее, чем yield, для выбора прокси
# добавил запись неспарсенных страниц
# добавил повторный парсинг неспарсенных страниц
# убрал мультипроцессинг из-за багов Винды
# todo: не придумал сделать счётчик категорий


import requests
import csv
import certifi
import lxml
from bs4 import BeautifulSoup
from datetime import datetime
# from multiprocessing import Pool
from random import uniform, choice
from time import sleep


# глобально объявляем данные, необходимые для избежания бана
global useragent_list, proxy_list

# получаем генератор списка юзер-агентов из файла
with open("useragents.txt", "r") as f:
    useragent_list = f.read().split('\n')

# получаем генератор списка прокси из файла (прокси проверять отдельно!)
with open("proxylist.txt", "r") as f:
    proxy_list = f.read().split('\n')


def get_response(url, useragent={'User-Agent': 'Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0'},
                 proxy={'http': 'http://37.187.127.216:8080', 'https': 'http://37.187.127.216:8080'}):
    """ Получаем ответ страницы по урл с паузой. Ожидаем <Response [200]>"""
    print('Trying to parse', url)
    timeout = uniform(30, 40)
    try:
        response = requests.get(url, headers=useragent, proxies=proxy, timeout=timeout, verify=certifi.where())
        # делаем паузу
        pause = uniform(3, 6)
        sleep(pause)
        return response
    # в случае бана пробуем снова с бОльшей паузой
    except requests.exceptions.RequestException as e:
        print(f'Error for {url}. More info:', e)
        useragent = {'User-Agent': choice(useragent_list)}
        proxy = {'http': choice(proxy_list), 'https': choice(proxy_list)}
        write_not_parsed(url)    # записываем страницу с ошибкой
        pause = uniform(10, 15)
        sleep(pause)
        get_response(url, useragent=useragent, proxy=proxy)
    except Exception as e:
        # непредусмотренные ошибки
        write_not_parsed(url)
        print(f'Another Error for {url} in get_response():', e)


def get_category_links(dom):
    """ Находим на странице входа ссылки на категории. Ожидаем список со ссылками """
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


def write_not_parsed(url):
    """ Записываем необработанные страницы """
    with open('notparsed.txt', 'a', newline='') as f:
        f.write(url + '\n')


def write_csv(data):
    """ Записываем данные в csv """
    with open('uniqom.csv', 'a', newline='') as csv_file:
        writer = csv.writer(csv_file, delimiter=';')
        writer.writerow(data)


def category_decorator(parse):
    """ Получаем количество страниц в категории, парсим их в цикле """
    def wrapper(response):
        category_url = response.url
        soup = BeautifulSoup(response.text, 'lxml')
        pagination = soup.find('ul', class_='uk-pagination')
        if not pagination:
            parse(response)
        else:
            parse(response)
            last_page = int(pagination.find_all('li')[-2].find('a').text.strip())
            page_number = 2
            while page_number <= last_page:
                next_page = ''.join([category_url, '&page=', str(page_number)])
                response = get_response(next_page)
                try:
                    soup = BeautifulSoup(response.text, 'lxml')
                    parse(response)
                except Exception as e:
                    print(f'Error in CatDec: {e}')
                page_number += 1
        # сообщаем, что вся категория спарсена
        title = soup.find('title').text.strip()
        # parsed_category_counter += 1
        # percent = round(parsed_category_counter / 271, 1)
        print(f'"{title}" has been parsed.')   # /n Progress: {parsed_category_counter} / 271 ({percent}%)
        wrapper._undecor = parse
    return wrapper


@category_decorator
def get_page_data(response):
    """ Парсим страницы категории товаров и пишем в csv """
    try:
        # извлекаем список товаров на странице, проходим по списку
        soup = BeautifulSoup(response.text, 'lxml')
        goods_rows = soup.find_all('div', class_='feip-productsList-product-row')
        for each in goods_rows:
            try:                # извлекаем артикул
                articul = each.find('div', class_='feip-productsList-product-articleID').text.strip()
            except:
                articul = ' '
            try:                # извлекаем изображение
                image = 'https:' + each.find('div', class_='feip-productsList-photoCell').find('a').get('href')
                if 'bw-logotype.png' in image:
                    image = 'no img'
            except:
                image = ' '
            try:                # извлекаем описание
                description = each.find('div', class_='feip-productsList-'
                                                      'product-variationLine').find('div').text.strip()
            except:
                description = ' '
            data = [articul, image, description]                # сохраняем в data, data пишем в csv
            write_csv(data)
        print(f'Page "{response.url}" has been parsed')
    except:
        print(f'No data here {response.url}')


def parse_categories(url):
    # оставляем только локальные склады, показ товаров по 100 на странице
    if 'deposits=2' not in url:
        url += '?&deposits=2&limit=100'
    # входим на страницу и парсим её
    try:
        response = get_response(url)
        if response.status_code == 200:
            get_page_data(response)
        else:
            print(f'Status {response.status_code} of page {url}')
    except Exception as e:
        print(f'Error for {url}:', e)
        write_not_parsed(url)


def time_decorator(func):
    """ Декоратор считает время выполнения всего скрипта """
    def wrapper():
        # начинаем отсчёт времени работы модуля
        start = datetime.now()
        print(f'Parsing started at {start}')
        func()
        # считаем и выводим затраченное время
        period = datetime.now() - start
        print('The End. Time wasted: ', str(period))
    return wrapper


@time_decorator
def main():
    # страница входа
    url = 'https://uniqom.ru/catalog'
    # получаем на странице входа список ссылок на страницы категорий
    index = get_response(url).text
    assert index is not None, 'Главная страница не отвечает'
    category_links = get_category_links(index)   # 271 категория

    # парсим категории
    for link in category_links:
        parse_categories(link)

    # код для парсинга N параллельными процессами
    # with Pool(N) as p:
    #     p.map(parse_categories, category_links)

    # повторно парсим страницы, на которых возникали ошибки
    with open("notparsed.txt", "r") as f:
        notparsed = set(f.read().split('\n'))
    # цикл повторяет parse_categories, но нужен get_page_data без декоратора
    for url in notparsed:
        try:
            response = get_response(url)
            get_page_data._undecor(response)
        except Exception as e:
            print(f'Error for {url}:', e)
            write_not_parsed(url)


if __name__ == '__main__':
    main()
