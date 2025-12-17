import pyautogui
import pyperclip
import random
import time

from torch.cuda import clock_rate

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5
interval_time = 3


def click(locate):
    pyautogui.click(locate[0], locate[1], interval=random.random() / interval_time)


def write(message):
    pyperclip.copy(message)
    pyautogui.hotkey('ctrl', 'v', interval=random.random() / interval_time)


def clear():
    pyautogui.hotkey('ctrl', 'a', interval=random.random() / interval_time)
    pyautogui.press('backspace', interval=random.random() / interval_time)


def process(data, component):
    groupName = data.get('groupName')
    message = data.get('message')
    msg_area = component['msg_area']
    search_area = component['search_area']
    choose_area = component['choose_area']
    for i in groupName:
        print("查找群:{},并准备发送信息.".format(i))
        click(search_area)
        clear()
        write(i)
        time.sleep(0.5)
        click(choose_area)
        time.sleep(0.5)
        click(msg_area)
        write(message)
        pyautogui.press('enter', interval=random.random() / interval_time)
        print('群消息:{},已成功发送至:{}.'.format(groupName, message))
