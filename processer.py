from sympy import false

from ui_controller import *

province_abbr_map = {
    "北京市": "京",
    "天津市": "津",
    "河北省": "冀",
    "山西省": "晋",
    "内蒙古自治区": "蒙",
    "辽宁省": "辽",
    "吉林省": "吉",
    "黑龙江省": "黑",
    "上海市": "沪",
    "江苏省": "苏",
    "浙江省": "浙",
    "安徽省": "皖",
    "福建省": "闽",
    "江西省": "赣",
    "山东省": "鲁",
    "河南省": "豫",
    "湖北省": "鄂",
    "湖南省": "湘",
    "广东省": "粤",
    "广西壮族自治区": "桂",
    "海南省": "琼",
    "重庆市": "渝",
    "四川省": "川",
    "贵州省": "黔",  # 通常使用“黔”
    "云南省": "云",
    "西藏自治区": "藏",
    "陕西省": "陕",
    "甘肃省": "甘",
    "青海省": "青",
    "宁夏回族自治区": "宁",
    "新疆维吾尔自治区": "新",
    "香港特别行政区": "港",
    "澳门特别行政区": "澳",
    "台湾省": "台"
}


class Process:
    def __init__(self):
        self.last_result = None

    def check_repeat(self, res, components):
        create_ocr_image(components['ocr_left_top_x'], components['ocr_left_top_y'],
                         components['ocr_right_bottom_x'], components['ocr_right_bottom_y'])
        result = parse_result(read())
        if res[-1] == result[-1]:
            print('检测到滚动条结束，停止本次群发')
            return False
        self.last_result = result
        return True

    def process(self, data, components):
        msg_area = [components['msg_area_x'], components['msg_area_y']]
        send_button = [components['send_button_x'], components['send_button_y']]
        directions = data.get('directions')
        message = data.get("message")
        pyperclip.copy(message)
        province = data.get('province')
        province_abbr = province_abbr_map.get(province)
        keywords = ['亿旅通', '专属服务群']
        if province_abbr:
            keywords.append(province_abbr)
        else:
            return
        print(keywords)
        create_ocr_image(components['ocr_left_top_x'], components['ocr_left_top_y'],
                         components['ocr_right_bottom_x'], components['ocr_right_bottom_y'])
        self.last_result = parse_result(read())
        send_result = check_keyword(keywords, self.last_result)
        if not len(send_result) == 0:
            print('检测到群聊:{}，开始发送'.format(send_result))
            send_msg(msg_area, send_button, send_result,
                     [components['ocr_left_top_x'], components['ocr_left_top_y']])
        scroll_msg_panel(components, directions)
        while self.check_repeat(self.last_result, components):
            send_result = check_keyword(keywords, self.last_result)
            if not len(send_result) == 0:
                print('检测到群聊:{}，开始发送'.format(send_result))
                send_msg(msg_area, send_button, send_result,
                         [components['ocr_left_top_x'], components['ocr_left_top_y']])
            scroll_msg_panel(components, directions)
