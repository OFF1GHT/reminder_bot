import os
import telebot
import datetime
import threading
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Получаем токен из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Создаем объект бота с использованием токена из переменной окружения
bot = telebot.TeleBot(BOT_TOKEN)

# Храним напоминания и таймеры для каждого пользователя
reminders = {}
reminder_timers = {}

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    commands = """
    Привет! Я бот-напоминалка. Вот список доступных команд:
    /reminder - Создать новое напоминание.
    /view_reminders - Посмотреть все напоминания.
    /delete_reminder - Удалить напоминание.
    /update_reminder - Изменить напоминание.
    """
    bot.send_message(message.chat.id, commands)

# Обработчик команды /reminder
@bot.message_handler(commands=['reminder'])
def reminder_message(message):
    bot.send_message(message.chat.id, 'Введите название напоминания:')
    bot.register_next_step_handler(message, set_reminder_name)

# Функция для установки названия напоминания
def set_reminder_name(message):
    user_data = {}
    user_data[message.chat.id] = {'reminder_name': message.text}
    bot.send_message(message.chat.id, 'Введите дату и время, когда вы хотите получить напоминание в формате ДД.ММ.ГГГГ чч:мм.')
    bot.register_next_step_handler(message, reminder_set, user_data)

# Функция для установки напоминания
def reminder_set(message, user_data):
    try:
        reminder_time = datetime.datetime.strptime(message.text, '%d.%m.%Y %H:%M')
        now = datetime.datetime.now()
        delta = reminder_time - now
        if delta.total_seconds() <= 0:
            bot.send_message(message.chat.id, 'Вы ввели прошедшую дату, попробуйте еще раз.')
        else:
            reminder_name = user_data[message.chat.id]['reminder_name']
            
            if message.chat.id not in reminders:
                reminders[message.chat.id] = []
            if message.chat.id in reminder_timers:
                for timer in reminder_timers[message.chat.id]:
                    timer.cancel()
            reminder_timers[message.chat.id] = []

            reminders[message.chat.id].append({
                'name': reminder_name,
                'time': reminder_time
            })

            bot.send_message(message.chat.id, f'Напоминание "{reminder_name}" установлено на {reminder_time.strftime("%d.%m.%Y %H:%M")}.')
            
            reminder_timer = threading.Timer(delta.total_seconds(), send_reminder, [message.chat.id, reminder_name])
            reminder_timers[message.chat.id].append(reminder_timer)
            reminder_timer.start()

    except ValueError:
        bot.send_message(message.chat.id, 'Вы ввели неверный формат даты и времени, попробуйте еще раз.')

# Функция, которая отправляет напоминание пользователю
def send_reminder(chat_id, reminder_name):
    bot.send_message(chat_id, f'Время получить ваше напоминание "{reminder_name}"!')

# Команда для просмотра всех напоминаний
@bot.message_handler(commands=['view_reminders'])
def view_reminders(message):
    if message.chat.id in reminders and reminders[message.chat.id]:
        response = 'Ваши напоминания:\n'
        for i, reminder in enumerate(reminders[message.chat.id]):
            response += f"{i + 1}. {reminder['name']} — {reminder['time'].strftime('%d.%m.%Y %H:%M')}\n"
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, 'У вас нет напоминаний.')

# Команда для удаления напоминания
@bot.message_handler(commands=['delete_reminder'])
def delete_reminder(message):
    if message.chat.id in reminders and reminders[message.chat.id]:
        bot.send_message(message.chat.id, 'Введите номер напоминания, которое хотите удалить:')
        bot.register_next_step_handler(message, delete_selected_reminder)
    else:
        bot.send_message(message.chat.id, 'У вас нет напоминаний для удаления.')

def delete_selected_reminder(message):
    try:
        index = int(message.text) - 1
        if 0 <= index < len(reminders[message.chat.id]):
            deleted_reminder = reminders[message.chat.id].pop(index)
            reminder_timers[message.chat.id][index].cancel()
            bot.send_message(message.chat.id, f'Напоминание "{deleted_reminder["name"]}" удалено.')
        else:
            bot.send_message(message.chat.id, 'Неверный номер напоминания.')
    except ValueError:
        bot.send_message(message.chat.id, 'Введите корректный номер.')

# Команда для обновления напоминания
@bot.message_handler(commands=['update_reminder'])
def update_reminder(message):
    if message.chat.id in reminders and reminders[message.chat.id]:
        bot.send_message(message.chat.id, 'Введите номер напоминания, которое хотите изменить:')
        bot.register_next_step_handler(message, update_selected_reminder)
    else:
        bot.send_message(message.chat.id, 'У вас нет напоминаний для изменения.')

def update_selected_reminder(message):
    try:
        index = int(message.text) - 1
        if 0 <= index < len(reminders[message.chat.id]):
            bot.send_message(message.chat.id, 'Введите новое название напоминания:')
            bot.register_next_step_handler(message, set_new_reminder_name, index)
        else:
            bot.send_message(message.chat.id, 'Неверный номер напоминания.')
    except ValueError:
        bot.send_message(message.chat.id, 'Введите корректный номер.')

def set_new_reminder_name(message, index):
    new_name = message.text
    reminders[message.chat.id][index]['name'] = new_name
    bot.send_message(message.chat.id, f'Название напоминания обновлено на "{new_name}".')

    reminder_time = reminders[message.chat.id][index]['time']
    delta = reminder_time - datetime.datetime.now()
    reminder_timers[message.chat.id][index].cancel()
    new_timer = threading.Timer(delta.total_seconds(), send_reminder, [message.chat.id, new_name])
    reminder_timers[message.chat.id][index] = new_timer
    new_timer.start()

# Обработчик любого сообщения от пользователя
@bot.message_handler(func=lambda message: True)
def handle_all_message(message):
    bot.send_message(message.chat.id, 'Я не понимаю, что вы говорите. Чтобы создать напоминание, введите /reminder.')

# Запуск бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
