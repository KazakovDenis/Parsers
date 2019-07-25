import requests    
import csv
import lxml
from bs4 import BeautifulSoup  
from datetime import datetime
from multiprocessing import Pool


def get_html(url):
  '''������� ��������� html-���� �������� �� ���'''
  html = requests.get(url)   # ���������� ������
  return html.text           # ���������� ������


def get_all_links(html): 
  ''' ������� ������� �� �������� ����� ������ �� �������� ��� �������� � ����� � ���� ������ '''
  soup = BeautifulSoup(html, 'lxml')
  # �������� ��� ���� <li> �� �������� � ��������� �������
  lis = soup.find_all('li', class_='feip-productsList-level4-label')
  links = []
  for li in lis:
      # �������� ������� href ���� <a>, ������������ ������ ������� <li>
      a = li.find('a').get('href')
      link = 'https://uniqom.ru' + a
      links.append(link)
  return links


def get_category_data(html):
  ''' ������� ������ �������� ��������� ������� � ���������� ������� � ������������ ������� '''
  soup = BeautifulSoup(html, 'lxml')
# ��������� ������ ������� �� ��������, �������� �� ������
  goods_rows = soup.find('div', class_='feip-productsList-product-row')
  data = {}
  for goods_row in goods_rows:
# ��������� �������
    try:
        articul = soup.find('div', class_='feip-productsList-product-articleID').text.strip()
    except:
        articul = 'articul exception'
# ��������� �����������
    try:
        image = 'https:' + soup.find('div', class_='feip-productsList-photoCell').find('a').get('href')
        if 'bw-logotype.png' in image:
            image = 'no img'
    except:
        image = 'img exception'
# ��������� ��������
    try:
        description = soup.find('div', class_='feip-productsList-product-variationLine').find('div').text.strip()
    except:
        description = 'description exception'
    data = {'articul': articul, 'image': image, 'description': description}

    # ��������� �� ���������
    # follow_next_page(soup)
  return data


def follow_next_page(soup):
  pagination = soup.find('li', class_='uk-pagination-next').find('a').get('href')
  next_page = 'https://uniqom.ru' + pagination
  make_all(next_page)


def write_csv(data):
  ''' ������� ���������� ������ � csv'''
  with open('uniqom.csv', 'a') as f:
    writer = csv.writer(f)
    writer.writerow( (data['articul'], data['image'], data['description']) ) 
  # ��������� 1 ��������, ������� ������
    print(data['articul'], 'is parsed')


# ����� ������� ��� ������������� ��������
def make_all(url):
  html = get_html(url)
  data = get_category_data(html)
  write_csv(data)


# ����� ������ ������� ������� ���������� � ��������� @time_counter 
def main():
  # �������� ������ ������� ������ ������
  start = datetime.now()

  # �������� �� �������� ����� ������ ������ �� �������� ��������� 
  url = 'https://uniqom.ru/catalog'
  all_links = get_all_links( get_html(url) )

  # ��� ��� �������� 4-�� ������������� ����������
  with Pool(1) as p:
      p.map(make_all, all_links)

  # ��� ��� ����������������� �������� ����� ���������
  #categories_count = len(all_links)      
  #for index, url in enumerate(all_links):
    #html = get_html(url)
    #data = get_category_data(html)
    #write_csv(data)
    #print(f'��������: {index} / {categories_count}')  

  period = datetime.now() - start
  print('����� ��������: ', str(period))


if __name__ == '__main__':
    main()
    

