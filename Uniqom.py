import requests    
import csv
import lxml
from bs4 import BeautifulSoup  
from datetime import datetime
from multiprocessing import Pool


def get_html(url):
  '''Функция получения html-кода страницы по урл'''
  html = requests.get(url)   # возвращает объект
  return html.text           # возвращает строку


def get_all_links(html): 
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


def get_category_data(html):
  ''' Функция парсит страницы категории товаров и возвращает словарь с извлечёнными данными '''
  soup = BeautifulSoup(html, 'lxml')
# извлекаем список товаров на странице, проходим по списку
  goods_rows = soup.find('div', class_='feip-productsList-product-row')
  data = {}
  for goods_row in goods_rows:
# извлекаем артикул
    try:
        articul = soup.find('div', class_='feip-productsList-product-articleID').text.strip()
    except:
        articul = 'articul exception'
# извлекаем изображение
    try:
        image = 'https:' + soup.find('div', class_='feip-productsList-photoCell').find('a').get('href')
        if 'bw-logotype.png' in image:
            image = 'no img'
    except:
        image = 'img exception'
# извлекаем описание
    try:
        description = soup.find('div', class_='feip-productsList-product-variationLine').find('div').text.strip()
    except:
        description = 'description exception'
    data = {'articul': articul, 'image': image, 'description': description}

    # переходим по пагинации
    # follow_next_page(soup)
  return data


def follow_next_page(soup):
  pagination = soup.find('li', class_='uk-pagination-next').find('a').get('href')
  next_page = 'https://uniqom.ru' + pagination
  make_all(next_page)


def write_csv(data):
  ''' Функция записывает данные в csv'''
  with open('uniqom.csv', 'a') as f:
    writer = csv.writer(f)
    writer.writerow( (data['articul'], data['image'], data['description']) ) 
  # принимает 1 аргумент, поэтому кортеж
    print(data['articul'], 'is parsed')


# пишем функцию для параллельного парсинга
def make_all(url):
  html = get_html(url)
  data = get_category_data(html)
  write_csv(data)


# позже вынесу подсчёт времени выполнения в декоратор @time_counter 
def main():
  # начинаем отсчёт времени работы модуля
  start = datetime.now()

  # получаем на странице входа список ссылок на страницы категорий 
  url = 'https://uniqom.ru/catalog'
  all_links = get_all_links( get_html(url) )

  # код для парсинга 4-мя параллельными процессами
  with Pool(1) as p:
      p.map(make_all, all_links)

  # код для последовательного парсинга одним процессом
  #categories_count = len(all_links)      
  #for index, url in enumerate(all_links):
    #html = get_html(url)
    #data = get_category_data(html)
    #write_csv(data)
    #print(f'Прогресс: {index} / {categories_count}')  

  period = datetime.now() - start
  print('Время парсинга: ', str(period))


if __name__ == '__main__':
    main()
    

