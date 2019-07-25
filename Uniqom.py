import requests, csv, lxml
from bs4 import BeautifulSoup  
from datetime import datetime
from multiprocessing import Pool


def get_html(url):
  '''Функция получения html-кода страницы по урл'''
  html = requests.get(url)   # возвращает объект
  return html.text           # возвращает строку


def get_category_links(html):
  ''' Функция находит на странице входа ссылки на страницы для парсинга и выдаёт в виде списка '''
  soup = BeautifulSoup(html, 'lxml')
  # получаем все теги <li> на странице с указанным классом
  lis = soup.find_all('li', class_='feip-productsList-level4-label')
  links = []
  for li in lis:
      # получаем атрибут href тега <a>, находящегося внутри каждого <li>
      a = li.find('a').get('href')
      link = 'https://uniqom.ru' + a
      links.append(link)
  return links


def write_csv(data, articul):
  ''' Функция записывает данные в csv'''
  with open('uniqom.csv', 'a', newline='') as csv_file:
    writer = csv.writer(csv_file, delimiter=';')
    writer.writerow(data)
  print(f'{articul} has been parsed')


def get_category_data(html):
  ''' Функция парсит страницы категории товаров и возвращает словарь с извлечёнными данными '''
  soup = BeautifulSoup(html, 'lxml')
# извлекаем список товаров на странице, проходим по списку
  goods_rows = soup.find_all('div', class_='feip-productsList-product-row')
  data = []
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
        description = each.find('div', class_='feip-productsList-product-variationLine').find('div').text.strip()
    except:
        description = 'description exception'
        
    data = [articul, image, description]
    write_csv(data, articul)
    # переходим по пагинации
  follow_next_page(soup)


def follow_next_page(soup):
  '''Функция переходит на следующую страницу внутри категории товаров'''
  try:
    pagination = soup.find('li', class_='uk-pagination-next').find('a').get('href')
    next_page = 'https://uniqom.ru' + pagination
    parse_pages(next_page)
  except:
    pass


# пишем функцию для параллельного парсинга
def parse_pages(url):
  html = get_html(url)
  get_category_data(html)


def time_file_decorator(func):
  ''' Декоратор считает время выполнения всего скрипта и открывает/закрывает файл для записи'''
  def wrapper():
    # начинаем отсчёт времени работы модуля
    start = datetime.now()
    print(f'Parsing started at {start}')
    # не удалось решить проблему выноса открытия файла в декоратор
    # файл читается, но не пишется
    # global csv_file
    # with open('uniqom.csv', 'a', newline='') as csv_file:
    func()
    # считаем и выводим затраченное время
    period = datetime.now() - start
    print('Time wasted: ', str(period))
  return wrapper


@time_file_decorator
def main():
  # получаем на странице входа список ссылок на страницы категорий 
  url = 'https://uniqom.ru/catalog'
  all_links = get_category_links( get_html(url) )

  # код для парсинга N параллельными процессами
  with Pool(4) as p:
      p.map(parse_pages, all_links[1:2]) 


if __name__ == '__main__':
    main()
    

