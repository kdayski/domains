import requests
import time
import urllib.request, json
import os
# import logging
# try:
#     import http.client as http_client
# except ImportError:
#     import httplib as http_client
# http_client.HTTPConnection.debuglevel = 1

# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

session = requests.session()

def remove_files():
    dirs = os.listdir('.')
    for d in dirs:
        if '.' in d: continue
        direc = os.listdir(f'{d}')
        for i in direc:
            files = os.listdir(f'{d}/{i}/')
            for j in files:
                os.remove(f'{d}/{i}/{j}')

def make_request(url):

    headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'
    }
    r = session.get(url, headers=headers, timeout=5)
    return r.text.encode('utf-8').decode('cp1251')

def get_key(url):

    main_html = make_request(url)
    hrefs = main_html.split('<A HREF="')
    for i in hrefs:
        if 'searchss' in i:
            last_index = i.find('"')
            searchss = i[:last_index]
    key = searchss.split('state=')[1]
    info = {'searchss': searchss, 'key': key}
    return info

def make_html_file(src, html):

    with open(f'{src}.html', 'w') as output_file:
        output_file.write(html)

name = input('insert word\n')
fp_url = 'http://tmsearch.uspto.gov/'
info = get_key(fp_url)
key = info['key']

remove_files()

fp_html = make_request(fp_url)
make_html_file('html/main_pages/first_page', fp_html)

sp_url = fp_url + info['searchss']
sp_html = make_request(sp_url)
make_html_file('html/main_pages/second_page', sp_html)

tp_url = f'http://tmsearch.uspto.gov/bin/showfield?f=toc&state={key}&p_search=searchss&p_L=50&BackReference=&p_plural=yes&p_s_PARA1=live&p_tagrepl%7E%3A=PARA1%24LD&PARA2&p_s_PARA2={name}&p_tagrepl%7E%3A=PARA2%24COMB&p_op_ALL=AND&a_default=search&a_search=Submit+Query&a_search=Submit+Query'
tp_html = make_request(tp_url)
make_html_file('html/main_pages/third_page', tp_html)

hrefs = tp_html.split('<A HREF="')
TSDRS = []
for i in hrefs:
    if 'TSDR' in i:
        last_index = i.find('"')
        TSDRS.append(i[:last_index])

TEASES = []
for i in TSDRS:
    number = (i.split('caseNumber=')[1]).split('&')[0]
    url = f'https://tsdr.uspto.gov/docsview/sn{number}'
    cnt = 0
    while True:
        if cnt == 10: make_html_file(f'html/TSDRS/TSDR_{number}', 'reached the limit of requests')
        try: html = make_request(url)
        except: make_html_file(f'html/TSDRS/TSDR_{number}', 'permission denied')
        if '503 Service Unavailable' not in html: break
        cnt += 1
    make_html_file(f'html/TSDRS/TSDR_{number}', html)
    hrefs = html.split('<a href="')
    for i in hrefs:
        RF_index = i.find('TEAS RF New Application')
        Plus_index = i.find('TEAS Plus New Application')
        if (RF_index != -1 or Plus_index != -1):
            last_index = i.find('"')
            href = i[:last_index]
            doc_id = href.split('docId=')[1]
            url = f'https://tsdrsec.uspto.gov/ts/cd/casedoc/sn{number}/{doc_id}/1/webcontent?scale=1'
            TEASES.append(url)

def parse_tags(string, tag):
    try:
        if tag == 'th': content = string.split('<td')[0]
        else: content = string.split('<td')[1]
        last_index = content.find('</')
        content = content[:last_index]
        content_reverse = ''
        for i in range(len(content)):
            if content[-i-1] == '>': break
            content_reverse += content[-i-1]
        content = ''
        for i in range(len(content_reverse)):
            content += content_reverse[-i-1]

        if content == '*':
            content = string.split('<td')[0]
            first_index = content.find('font>')
            content = content[first_index:]
            last_index = content.find('</font>')
            content = content[5:last_index]

        if content == '' and tag == 'th':
            content = string.split('<td')[0]
            first_index = content.find('</a>')+4
            content = content[first_index:]
            last_index = content.find('</font')
            content = content[:last_index]

        if content == '': return 'empty'

        if '/a>' in content:
            first_index = content.find('/a>')
            content = content[first_index+3:]

        return content.strip()

    except: 
        return "empty"

index = 0
domains = []
for i in TEASES:
    html = make_request(i)
    make_html_file(f'html/TEASES/TEAS_{index}', html)
    table = html.split('<tr bgcolor="')[1].replace('&nbsp;', '')
    trs = table.replace('\t', '').replace('\n', '').split('<tr')
    make_html_file(f'html/Documents/Document_{index}', table)
    dict_of_info = {}
    for i in range(1, len(trs)):
        th = parse_tags(trs[i], 'th')
        td = parse_tags(trs[i], 'td')
        if td == 'empty' and th == 'empty': continue
        dict_of_info[th] = td
        if '@' in td:
            if ';' in td:
                mails = td.split(';')
                for i in mails: domains.append(i.strip())
            else: domains.append(td)

    with open(f'py/parsed_TSDRs/TSDR_{index}.py', 'w') as result:
        result.write(f'dict_of_info = {str(dict_of_info)}')
    
    index += 1

domain = set()
for i in domains:
    domain.add(i.split('@')[1])
domains = domain

cnt = 0
for domain in domains:
    url = f'http://api.whois.vu/?q={domain}'
    try:
        with urllib.request.urlopen(url) as url:
            data = json.loads(url.read().decode())

        whois_arr = data['whois'].split('\r\n')
        data['whois'] = {}
        for i in whois_arr:
            if '>>>' in i or 'NOTICE' in i or 'URL of the ICANN' in i or 'TERMS OF USE' in i or 'You agree that' in i: continue
            if ': ' not in i: continue
            key_value = i.split(': ')
            key = key_value[0]
            value = key_value[1]
            data['whois'][key] = value

        with open(f'py/parsed_domains/domain_{cnt}.py', 'w') as dom_file:
            domain = domain.split('.')[0]
            dom_file.write(f'_{domain}={data}')
        cnt += 1
    except: pass
print('domain has been successfully parsed')