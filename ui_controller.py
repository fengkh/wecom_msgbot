from operator import truediv
import pyautogui
import time
import pyperclip  # 用于处理中文输入
from sympy.strategies.core import switch
import easyocr as ocr
import random

# 安全设置：鼠标移动到屏幕角落时停止程序
pyautogui.FAILSAFE = True
# 设置每个动作的间隔时间
pyautogui.PAUSE = 0.5


def create_ocr_image(ocr_left_top_x, ocr_left_top_y, ocr_right_bottom_x, ocr_right_bottom_y):
    temp_ocr_image = pyautogui.screenshot(region=(ocr_left_top_x, ocr_left_top_y, (ocr_right_bottom_x - ocr_left_top_x),
                                                  (ocr_right_bottom_y - ocr_left_top_y)))
    temp_ocr_image.save('temp_ocr_image.png')
    return temp_ocr_image


def scroll_msg_panel(components, direction):
    time.sleep(2)
    pyautogui.click(components['ocr_left_top_x'], components['ocr_left_top_y'], interval=random.random() / 3)
    if direction:
        pyautogui.scroll(-10000)
    else:
        pyautogui.scroll(10000)


def send_msg(msg_area, send_button, send_result, bias):
    for i in send_result:
        pyautogui.click(i[0] + bias[0], i[1] + bias[1], interval=random.random() / 3)
        pyautogui.click(msg_area[0], msg_area[1], interval=random.random() / 3)
        pyautogui.hotkey('ctrl', 'v', interval=random.random() / 3)
        pyautogui.click(send_button[0], send_button[1], interval=random.random() / 3)


def read():
    reader = ocr.Reader(['ch_sim'])
    result = reader.readtext('temp_ocr_image.png')
    return result


def parse_result(result):
    json_result = []
    for (bbox, text, prob) in result:
        print(f"Detected text: {text}, Probability: {prob}, Bounding Box: {bbox}")
        json_result.append({'text': text, 'prob': float(prob), 'center_x': int(bbox[1][0] + bbox[0][0]) / 2,
                            'center_y': int(bbox[2][1] + bbox[1][1]) / 2})
    print(json_result)
    return json_result


def check_keyword(keywords, result):
    checked_result = []
    for i in result:
        if all(keyword in i['text'] for keyword in keywords) and i['prob'] > 0.5:
            checked_result.append([i['center_x'], i['center_y']])
            print('成功匹配到:{}'.format(i['text']))
    return checked_result
