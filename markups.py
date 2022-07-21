from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.callback_data import CallbackData


def auth(cb: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    button = InlineKeyboardButton(text='Привязать свой аккаунт Яндекс Музыки', callback_data=cb)
    markup.add(button)
    return markup


