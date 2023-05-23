from CONSTANT_INFO import exchange_bot_token as BOT_TOKEN, value_token as VALUE_TOKEN#импортирую токен своего бота и токен для апи курса валют(дальше "Валютный токен")(можно получить здесь: https://app.currencyapi.com/api-keys) из личного файла
from CONSTANT_INFO import redis_host, redis_password, redis_port #импортирую свои данные redis из личного файла
import extentions as ex #импортирую класс своего парсера
import telebot
import redis 

red = redis.Redis(redis_host, redis_port, password=redis_password) #подключаемся к своей БД redis
bot = telebot.TeleBot(BOT_TOKEN) #создаем бота

keyboard = telebot.types.InlineKeyboardMarkup()#создаем доску для кнопок
previos_request_button = telebot.types.InlineKeyboardButton('Прислать последний\nзапрос курса', callback_data='previous_request') #кнопка предыдущего запрос
commands_button = telebot.types.InlineKeyboardButton('Доступные команды', callback_data='commands') #кнопка доступных комманд
keyboard.add(previos_request_button)#добавляем кнопки на доску
keyboard.add(commands_button)


@bot.message_handler(commands = ['start', 'help']) #обработчик команд /star и /help
def send_instructions(message):
    bot.send_message(message.chat.id, ex.INSTRUCTION, reply_markup=keyboard)#отправка сообщения с инструкцией

@bot.message_handler(commands=['values'])#обработчик команды /values
def send_possible_values(message):
    chat_id = message.chat.id #id чата из которого пришло сообщение
    try:
        parser = ex.ValueParser(VALUE_TOKEN)#создаём объект класса ValueParser c нашим токеном
        possible_value_names = parser.value_names()
        list_send = '\n'.join(possible_value_names)#список, который будет отправлен в ответ пользователю
        bot.send_message(chat_id, f'Доступные валюты: \n {list_send}', reply_markup=keyboard)
    except ex.ServerError as servererror:
        bot.send_message(chat_id, servererror.message)

@bot.message_handler(content_types=['text'])#обработчик обычных сообщений
def send_exchange(message):
    chat_id = message.chat.id 
    user_id = message.from_user.id
    try:
        parser = ex.ValueParser(VALUE_TOKEN)
        text = message.text #сообщение пользователя
        input_values = parser.string_parser(text) #обрабатываем сообщение пользователя, возвращается список вида ['количество валюты', 'валюта, в которую перевести', 'валюта, из которой перевести']
        amount, quote, base = input_values[0], input_values[1], input_values[2] #забираем результат обработки сообщения в переменные
        rate = parser.get_price(base, quote, amount) #получаем курс
        output = f'{amount} {base}\n = \n{rate} {quote}' #формируем вывод
        bot.send_message(chat_id, output, reply_markup=keyboard)
        casher = ex.Id_Casher(red)
        casher.send_cashe(str(user_id), text)
    except ex.APIException as apierror: 
        bot.send_message(chat_id, apierror.message, reply_markup=keyboard)
    except ex.ServerError as servererror:
        bot.send_message(chat_id, servererror.message)

@bot.callback_query_handler(func = lambda call: call.data == 'previous_request') #обработка кнопки previous_request_button
def send_previous_request(message):
    user_id = message.from_user.id
    casher = ex.Id_Casher(red)
    try:
        parser = ex.ValueParser(VALUE_TOKEN)
        text = casher.get_cashe(str(user_id)) #получаем предыдущий запрос
        input_values = parser.string_parser(text) #обрабатываем предыдущий запрос, возвращается список вида ['количество валюты', 'валюта, в которую перевести', 'валюта, из которой перевести']
        amount, quote, base = input_values[0], input_values[1], input_values[2] #забираем результат обработки предыдущего запроса в переменные
        rate = parser.get_price(base, quote, amount) #получаем курс
        output = f'{amount} {base}\n = \n{rate} {quote}' #формируем вывод
        bot.send_message(user_id, output, reply_markup=keyboard)
    except ex.KeyNotExistsError as keyerror: #если данных предыдущего запроса нет, то взываем исключение
        bot.send_message(user_id, 'Вы не запрашивали ничего раньше')

@bot.callback_query_handler(func = lambda call: call.data == 'commands') #обработчик кнопки commands
def send_commands(message):
    user_id = message.from_user.id
    bot.send_message(user_id, ex.COMMANDS) #отправляем пользователю доступные команды

bot.polling()