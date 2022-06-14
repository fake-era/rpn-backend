import json
import asyncio
import aiohttp
from cert import cert
import requests
from bs4 import BeautifulSoup as bs
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import crud
import time
from schemas import Result as SchemaResult
from schemas import Token as SchemaToken

urllib3.disable_warnings(InsecureRequestWarning)


class BaseError(Exception):
    def __init__(self, code=None, message=None, **kwargs):
        self.code = code
        self.message = message
        for key, value in kwargs.items():
            setattr(self, key, value)


class AuthError(BaseError):
    pass


class EISZ:
    def __init__(self):
        self._base_url = 'https://www.eisz.kz/'
        self._session = requests.Session()
        self.module = {}

    def init_module(self):
        self.module['RPN'] = RPN(self._session)

    def _start_session(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0'
        }
        return self._session.get(self._base_url, headers=headers, verify=False)

    @staticmethod
    def _get_request_verification_token(response):
        soup = bs(response.text, 'html.parser')
        signup_box = soup.find('div', class_='signup-box')
        try:
            request_verification_token = signup_box.find('input', {'name': "__RequestVerificationToken"})
        except AttributeError:
            request_verification_token = None
        if request_verification_token is None:
            return request_verification_token
        else:
            return request_verification_token['value']

    def auth(self):
        response = self._start_session()
        soup = bs(response.text, 'html.parser')
        signup_box = soup.find('div', class_='signup-box')
        if signup_box is not None:
            start_url = response.url
            login_url = f'{self._base_url}edslogin?ReturnUrl=%2F'
            request_verification_token = self._get_request_verification_token(response)
            if request_verification_token is not None:
                headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,'
                              '*/*;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Host': 'www.eisz.kz',
                    'Origin': 'https://www.eisz.kz',
                    'Referer': start_url
                }
                payload = f'__RequestVerificationToken={request_verification_token}&' \
                          f'certificate={cert}&isLogged=false'
                response = self._session.post(login_url, data=payload, headers=headers, verify=False)
                if response.status_code != 200:
                    raise AuthError(response.status_code, response.text)


class RPN:
    def __init__(self, session=requests.Session()):
        self._base_url = 'https://rpn.eisz.kz'
        self._session = session

    def start_session(self):
        try:
            return self._session.get(self._base_url, verify=False)
        except requests.exceptions.TooManyRedirects:
            pass

    def get_token(self):
        response = self._session.get(f'{self._base_url}/Account/GetToken', verify=False, allow_redirects=False)
        result = response.text
        return result

    @staticmethod
    async def _get_json(client, url):
        async with client.get(url, ssl=False) as response:
            assert response.status == 200
            return await response.json()

    async def get_person_id_by_iin(self, client, fioiin, numerical):
        url = f'{self._base_url}/services/api/person/person?fioiin={fioiin}&page=1&pagesize=1&_={numerical}'
        person_id = asyncio.create_task(self._get_json(client, url))
        await asyncio.gather(person_id)
        return person_id.result()

    async def get_person(self, client, person_id, numerical):
        urls = [
            f'{self._base_url}/services/api/person/getPersonByIdInternal/{person_id}?_={str(int(numerical) + 1)}',
            f'{self._base_url}/services/api/person/{person_id}/addresses?_={str(int(numerical) + 2)}',
            f'{self._base_url}/services/api/person/{person_id}/relatives?_={str(int(numerical) + 3)}',
            f'{self._base_url}/services/api/person/{person_id}/getPhonesForSite?_={str(int(numerical) + 4)}'
        ]
        person = asyncio.create_task(self._get_json(client, urls[0]))
        addresses = asyncio.create_task(self._get_json(client, urls[1]))
        relatives = asyncio.create_task(self._get_json(client, urls[2]))
        numbers = asyncio.create_task(self._get_json(client, urls[3]))
        await asyncio.gather(person, addresses, relatives, numbers)
        data = {
            'person': person.result(),
            'numbers': numbers.result(),
            'relatives': relatives.result(),
            'address': addresses.result(),
        }
        return data


def get_token():
    client = EISZ()
    client.auth()
    client.init_module()
    rpn: RPN = client.module['RPN']
    rpn.start_session()
    token = rpn.get_token()
    data_dict = {
        'token': token
    }
    crud.create_token(SchemaToken(**data_dict))
    return token


async def get_person(fioiin):
    db = crud.get_result_by_iin(fioiin)
    if db is None:
        numerical = '1121321321313'
        rpn = RPN()
        jwt_token = crud.get_last_token().token
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0',
            'Authorization': f'Bearer {jwt_token}',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Host': 'rpn.eisz.kz',
            'Referer': 'https://rpn.eisz.kz/'
        }
        client = aiohttp.ClientSession(headers=headers, trust_env=True)
        person_id = await rpn.get_person_id_by_iin(client, fioiin, numerical)
        person_id = person_id[0]['PersonID']
        data = await rpn.get_person(client, person_id, numerical)
        parsed_data = parse(data)
        result = SchemaResult(**parsed_data)
        check = crud.get_result_by_iin(result.iin)
        if check is None:
            crud.crete_result(result)
        else:
            crud.update_result(result)
        task_dict = {
            'iin': fioiin,
            'status': 'done'
        }
        task = SchemaTask(**task_dict)
        crud.update_task_status(task)
        await client.close()
        return result
    else:
        return SchemaResult.from_orm(db)


async def update_person(fioiin):
    numerical = '1121321321333'
    rpn = RPN()
    jwt_token = crud.get_last_token().token
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0',
        'Authorization': f'Bearer {jwt_token}',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        'Host': 'rpn.eisz.kz',
        'Referer': 'https://rpn.eisz.kz/'
    }
    client = aiohttp.ClientSession(headers=headers, trust_env=True)
    person_id = await rpn.get_person_id_by_iin(client, fioiin, numerical)
    person_id = person_id[0]['PersonID']
    data = await rpn.get_person(client, person_id, numerical)
    parsed_data = parse(data)
    result = SchemaResult(**parsed_data)
    crud.update_result(result)
    await client.close()
    return result


def parse(data: dict):
    try:
        iin = data['person']['iin']
    except Exception as e:
        iin = None
        BaseError(e)
    try:
        address = ' | '.join(d['addressString'] for d in data['address'])
    except Exception as e:
        print(e)
        address = ""
    try:
        numbers = ' | '.join(d['PhoneNumber'] for d in data['numbers'])
    except Exception as e:
        print(e)
        numbers = ""
    try:
        status_osms = data['person']['statusOsms']['nameRu']
    except Exception as e:
        print(e)
        status_osms = ""
    try:
        categories_osms = ' | '.join(d['nameRu'] for d in data['person']['categoriesOsms'])
    except Exception as e:
        print(e)
        categories_osms = ""
    try:
        relatives = ' | '.join(f"{r['Relative']['lastName']} {r['Relative']['firstName']} "
                               f"{r['Relative']['secondName']}"
                               for r in data['relatives'])
    except Exception as e:
        print(e)
        relatives = ""
    try:
        death_date = data['person']['death_date']
    except Exception as e:
        print(e)
        death_date = ""
    data = {
        'iin': iin,
        'address': address,
        'numbers': numbers,
        'status_osms': status_osms,
        'categories_osms': categories_osms,
        'relatives': relatives,
        'death_date': death_date
    }
    return data


async def main(iin):
    start = time.perf_counter()
    await get_person(iin)
    end = time.perf_counter()
    print(f'Общее затраченное время: {end - start} ')


if __name__ == '__main__':
    asyncio.run(main())
