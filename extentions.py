import requests
import json

INSTRUCTION = 'Этот бот переводит валюты по актуальному курсу!\n \n\
Чтобы получить результат,отправьте сообщение в формате: \n \
<валюта, из которой перевести> <валюта, в которою перевести> <количество валюты, из которой перевести> \n \n \
Чтобы узнать доступные для перевода валюты отправьте комманду /values'
COMMANDS = '/start - начать работу\n /help - инструкция \n /values доступные валюты\n'

class APIException(Exception): #класс исключения при ошибке ввода пользователя
    def __init__(self):
        self.message = 'ошибка со стороны пользователя'

class MonetaryUnitError(APIException): #исключение при вводе недопустимого значения валюты
    def __init__(self):
        self.message = 'Недопустимое значение денежной единицы'

class ValueNameError(APIException): #исключение при вводе недопустимого названия валюты
    def __init__(self):
        self.message ='Недопустимое название валюты'
    
class LessValuesError(APIException): #исключение при вводе мене двух названий валют
    def __init__(self):
        self.message ='Введено меньше двух валют'
    
class ServerError(Exception): #исключение при ошибке на сервере
    def __init__(self):
        self.message ='Ошибка со стороны сервера'

class KeyNotExistsError(Exception):
    def __init__(self):
        self.message = 'Несуществующий ключ'
    

class ValueParser: #класс парсера
    def __init__(self, token: str):
        self.token = token

    def value_names(self) -> list: #вывод возможных названий
        request = requests.get(f'https://api.currencyapi.com/v3/currencies?apikey={self.token}') #запрос к ресуру с курсами валют
        if request.ok:
            data = json.loads(request.content)['data'] #информация в ответ на запрос в виде словаря
            possible_values = [(value['name'],key) for (key, value) in data.items() if type(value) is dict] # пары название и обозначения валюты
            possible_value_names = sorted(list(set([i[0].lower() for i in possible_values])))#возможные названия валют валют в нижнем регистре
            return possible_value_names
        else:
            raise ServerError
    
    def value_symbol_dict(self) -> dict: #вывод словаря возможных названий и обозначений
        request = requests.get(f'https://api.currencyapi.com/v3/currencies?apikey={self.token}') #запрос к ресуру с курсами валют
        if request.ok:
            data = json.loads(request.content)['data'] #информация в ответ на запрос в виде словаря
            possible_values = [(value['name'].lower(),key) for (key, value) in data.items() if type(value) is dict] # пары название и обозначения валюты
            possible_values = {key:value for (key, value) in possible_values}#словарь с парами название:обозначение
            return possible_values
        else:
            raise ServerError
    
    def string_parser(self,string: str) -> dict: #парсинг текста сообщения
        word_list = string.lower().split() #приведение к нижнему регистру и разбитие строки на отдельные слова
        possible_value_names= self.value_names() #список для отбора и исключения имён валют
        try:
            monetary_unit_size = float(word_list[-1])#пытаемся взять значение валюты, если не является числом, вызываем исключение
            word_list.pop(-1) #удаляем значение из списка
        except ValueError:
            raise MonetaryUnitError
        values = [monetary_unit_size] #список, который будет возвращён функцией
        for _ in range(2): #обработка двух валют
            choise_list = possible_value_names.copy() #список для отбора названий валют
            word_list_copy = word_list.copy() #копия списка введенных пользователем слов
            counter = len(word_list_copy) #счётчик слов
            for word in reversed(word_list_copy):
                counter -= 1 #индекс текущего слова
                flag = False #показатель нахождения слова в названии
                for name in choise_list.copy(): #проходим по всем названиям
                    name = name.split() #разбиваем каждое название на список включенных в название слов
                    if word not in name: #проверяем входит ли слово в название
                        choise_list.remove(' '.join(name)) #если не входит, удаляем из списка
                    else:
                        flag = True #если входит хотя бы в одно из названий, то показатель становится True
                if not flag or len(choise_list) == 0: #если слово не вошло ни в одно из названий, то вызывается исключение
                    raise ValueNameError
                elif flag and len(choise_list) == 1: #проверяем, если осталось ли одно название
                    if choise_list[0] in ' '.join(word_list): #проверяем есть ли оставшееся название в введенных пользователем словах, если нет, вызываем исключение
                        values.append(choise_list[0]) #на первой итерации добавляется валюта, в которую нужно перевсти, на второй - валюта, из которой нужно перевести
                        length_last_value = len(values[-1].split()) #длина добавленного названия валюты
                        count = 0 #счетчик
                        while count < length_last_value: #удаляем обработаное название из списка слов
                                word_list.pop(-1)
                                count += 1
                        break
                    else:
                        raise ValueNameError
                elif counter == 0: #если дошло до первого слова, и оно есть в возможных названиях, но успешной обработки не прошло, вызываем исключение
                    raise ValueNameError
        if len(values) == 3:
            return values #возвращаем список вида ['количество валюты', 'валюта, в которую перевести', 'валюта, из которой перевести']
        else:
            raise LessValuesError
    
    def get_price(self, base, quote, amount) -> float: #получение курса
        possible_values = self.value_symbol_dict() #получаем словарь названий и обозначений
        to_value = possible_values[quote] #получаем нужные обозначения
        from_value = possible_values[base]
        request = requests.get(f'https://api.currencyapi.com/v2/latest?apikey={self.token}') #запрос актуального курса валют(в бесплатной версии валюты переводятся в доллары)
        if request.ok:
            data = json.loads(request.content)['data'] #курс всех валют в виде словаря
            rate = data[to_value]/data[from_value] * amount #курс заданных валют
            return rate #возвращаем курс
        else:
            raise ServerError

class Id_Casher(): #класс кэшера
    def __init__(self, redis_object): #принимает аргумент объект Redis
        self.red = redis_object

    def send_cashe(self, key: str, value: str): #отправляет в нашу бд ключ:значение
        self.red.set(key, value)
    
    def get_cashe(self, key: str): #получает из бд значение, если такой ключ существует в бд, инаще вызывает исключение
        if self.red.exists(key):
            return self.red.get(key).decode('UTF-8')
        else:
            raise  KeyNotExistsError
        
    


            



                
        
        


        





