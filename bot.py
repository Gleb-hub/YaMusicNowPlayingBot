import logging
import config
import hashlib
import pymongo.collection
import requests
from pymongo import MongoClient
from ya_music_manager import YaManager
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.mongo import MongoStorage
from aiogram.utils.callback_data import CallbackData
from aiogram.types import InlineQuery, InlineQueryResultCachedAudio, InlineQueryResultArticle, InputTextMessageContent
import yandex_music
import markups

API_TOKEN = '5402149220:AAGz0W6ftSXJGsBRMgFBU6hGH53AsaE5xFE'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
storage = MongoStorage(
    host='localhost',
    port='27017',
)
dp = Dispatcher(bot, storage=storage)
ym = YaManager()
tracks_db: pymongo.collection.Collection = MongoClient('mongodb://localhost:27017').tracks_db.tracks

auth_cb = CallbackData('auth', 'id', 'action')


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer('Привет! Я помогу тебе делиться любимыми треками со своими друзьями\n\nАвторизация в боте '
                         'абсолютно безопасна, я не храню ваши личные данные, кроме токена для работы с Яндекс '
                         'Музыкой\n\nЕсли вы обнаружили ошибку или у вас есть идея по улучшению, вы можете связаться '
                         'с разработчиком: @gl_epka\n\nВсе исходные файлы вы можете посмотреть на GitHub\'е '
                         '(ссылка в описании бота)',
                         reply_markup=markups.auth(auth_cb.new(id=message.chat.id, action='new')))


@dp.callback_query_handler(auth_cb.filter(action='new'))
async def auth_to_ya_music(query: types.CallbackQuery):
    user_data = await dp.storage.get_data(chat=query.message.chat.id)
    try:
        if user_data['auth_stat'] == 'completed':
            await query.message.edit_text('Вы уже зарегистрированы')
    except:
        user_data['auth_stat'] = 'login'
        await dp.storage.set_data(chat=query.message.chat.id, data=user_data)
        await query.message.edit_text(text='Чтобы зарегистрироваться отпрваьте команду '
                                           '/login <ваш логин> <ваш пароль>')


@dp.message_handler(commands=['login'])
async def registration(message: types.Message):
    user_data = await dp.storage.get_data(chat=message.chat.id)
    if user_data.get('auth_stat') == 'login':
        try:
            login = message.text.split(' ')[1]
            password = message.text.split(' ')[2]
            token = await ym.get_music_token(login, password)
            user_data['token'] = token
            user_data['auth_stat'] = 'completed'
            await dp.storage.set_data(chat=message.chat.id, data=user_data)
            await message.answer('Регистрация прошла успешно!\n\n Для безопасности можете удалить сообщение в котором '
                                 'вы отправляли логин и пароль\n\nЧтобы получить текущий трек: /current_track')
        except:
            await message.answer('Неверный логин или пароль, попробуй еще раз')
    elif user_data.get('auth_stat') == 'completed':
        await message.answer('Вы уже зарегистрированы!')
    else:
        await message.answer('Прежде чем начать регистрацию напишите команду /start')


@dp.message_handler(commands=['current_track'])
async def send_curr(message: types.Message):
    user_data = await dp.storage.get_data(chat=message.from_user.id)
    try:
        ym_track = ym.get_curr_track(user_data['token'])
        track_id = await get_track_tg_id(ym_track)
        await message.answer_audio(audio=track_id)
    except:
        await message.answer('У вас нет текущих треков\n\n(если это не так, тогда вы столкнулись с ошибкой которую я '
                             'не знаю как решить, напишите мне @gl_epka)')


@dp.message_handler(commands=['quit'])
async def quit_account(message: types.Message):
    user_data = await dp.storage.get_data(chat=message.from_user.id, default=None)

    if user_data is None or user_data.get('auth_stat') == 'login':
        await message.answer('Вы еще не зарегистрировались!')
    else:
        await dp.storage.set_data(chat=message.from_user.id, data=None)
        await message.answer('Вы вышли из своей учетной записи!')


@dp.message_handler(commands=['chat_id'])
async def send_group_id(message: types.Message):
    await message.answer(str(message.chat.id))


@dp.inline_handler()
async def inline_curr_track(inline_query: InlineQuery):
    user_data = await dp.storage.get_data(chat=inline_query.from_user.id, default=None)
    if user_data is None or user_data.get('auth_stat') == 'login' or user_data == {}:
        item = InlineQueryResultArticle(
            id=hashlib.md5('Что-то не так :('.encode()).hexdigest(),
            title='Что-то не так :(',
            input_message_content=InputTextMessageContent('Вы еще не зарегистрировались')
        )
        # don't forget to set cache_time=1 for testing (default is 300s or 5m)
        await bot.answer_inline_query(inline_query.id, results=[item], cache_time=10)
    else:
        ym_track = ym.get_curr_track(user_data['token'])
        track_id = await get_track_tg_id(ym_track)

        result_id: str = hashlib.md5(track_id.encode()).hexdigest()
        item = InlineQueryResultCachedAudio(
            id=result_id,
            audio_file_id=track_id
        )
        # don't forget to set cache_time=1 for testing (default is 300s or 5m)
        await bot.answer_inline_query(inline_query.id, results=[item], cache_time=10)


async def get_track_tg_id(ymt: yandex_music.Track) -> str:
    track = tracks_db.find_one({'ym-id': ymt.id})
    if track is None:
        url = ymt.get_download_info(get_direct_links=True)[0]['direct_link']
        artists = ', '.join(ymt.artists_name())
        r: types.Message = await bot.send_audio(chat_id=config.MUSIC_CHAT, audio=requests.get(url).content,
                                                title=ymt.title, performer=artists)

        tracks_db.insert_one({'ym-id': ymt.id, 'tg-id': r.audio.file_id})
        track_id = r.audio.file_id
    else:
        track_id = track['tg-id']
    return track_id


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
