import pyautogui
import time
import pyperclip  # 用于处理中文输入

# 安全设置：鼠标移动到屏幕角落时停止程序
pyautogui.FAILSAFE = True
# 设置每个动作的间隔时间
pyautogui.PAUSE = 0.5


class PyAutoGUIController:
    """PyAutoGUI控制器"""

    def __init__(self):
        # 获取屏幕尺寸
        self.screen_width, self.screen_height = pyautogui.size()
        print(f"屏幕尺寸: {self.screen_width} x {self.screen_height}")

    def mouse_operations(self):
        """鼠标操作"""
        print("\n=== 鼠标操作 ===")

        # 1. 获取当前鼠标位置
        current_x, current_y = pyautogui.position()
        print(f"当前鼠标位置: ({current_x}, {current_y})")

        # 2. 移动鼠标（绝对位置）
        pyautogui.moveTo(100, 100, duration=0.5)  # 0.5秒内移动到(100,100)
        print("已移动到 (100, 100)")

        # 3. 移动鼠标（相对位置）
        pyautogui.move(50, 50, duration=0.5)  # 向右移动50像素，向下移动50像素
        print("已相对移动 (50, 50)")

        # 4. 点击
        pyautogui.click()  # 当前位置单击
        pyautogui.click(x=200, y=200)  # 指定位置单击
        pyautogui.click(button='right')  # 右键单击
        pyautogui.click(clicks=2)  # 双击
        pyautogui.click(clicks=2, interval=0.25)  # 双击，间隔0.25秒

        # 5. 拖动
        pyautogui.dragTo(300, 300, duration=1)  # 拖动到指定位置
        pyautogui.drag(100, 0, duration=1, button='left')  # 向右拖动100像素

        # 6. 滚轮
        pyautogui.scroll(10)  # 向上滚动
        pyautogui.scroll(-10)  # 向下滚动

        # 7. 鼠标按下/释放
        pyautogui.mouseDown(x=400, y=400, button='left')
        time.sleep(0.5)
        pyautogui.mouseUp(x=400, y=400, button='left')

        # 8. 获取鼠标位置循环（用于定位元素）
        print("\n按 Ctrl+C 停止显示鼠标位置")
        try:
            while True:
                x, y = pyautogui.position()
                print(f'鼠标位置: ({x:4d}, {y:4d})', end='\r')
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n停止获取鼠标位置")

    def keyboard_operations(self):
        """键盘操作"""
        print("\n=== 键盘操作 ===")

        # 1. 输入文字（英文）
        pyautogui.write('Hello World!', interval=0.1)

        # 2. 输入文字（中文）- 使用pyperclip
        text_zh = "你好，世界！"
        pyperclip.copy(text_zh)  # 复制到剪贴板
        pyautogui.hotkey('ctrl', 'v')  # 粘贴

        # 3. 特殊按键
        pyautogui.press('enter')  # 按Enter键
        pyautogui.press('tab')  # 按Tab键
        pyautogui.press(['left', 'left', 'left'])  # 按左箭头3次

        # 4. 组合键
        pyautogui.hotkey('ctrl', 'c')  # 复制
        pyautogui.hotkey('ctrl', 'v')  # 粘贴
        pyautogui.hotkey('alt', 'f4')  # 关闭窗口

        # 5. 按下和释放
        pyautogui.keyDown('shift')  # 按下Shift
        pyautogui.press('a')  # 按A（得到大写A）
        pyautogui.keyUp('shift')  # 释放Shift

        # 6. 常用快捷键示例
        def common_hotkeys():
            pyautogui.hotkey('win', 'd')  # 显示桌面
            time.sleep(1)
            pyautogui.hotkey('win', 'r')  # 打开运行窗口
            time.sleep(0.5)
            pyautogui.write('notepad')
            pyautogui.press('enter')
            time.sleep(1)

        # 7. 输入特殊字符
        pyautogui.write(['!', '@', '#', '$', '%'], interval=0.1)

    def screenshot_and_locate(self):
        """截图和图像定位"""
        print("\n=== 截图和图像定位 ===")

        # 1. 全屏截图
        screenshot = pyautogui.screenshot()
        screenshot.save('screenshot.png')
        print("已保存截图: screenshot.png")

        # 2. 区域截图
        region_screenshot = pyautogui.screenshot(region=(0, 0, 300, 400))
        region_screenshot.save('region_screenshot.png')

        # 3. 获取像素颜色
        pixel_color = pyautogui.pixel(100, 200)
        print(f"位置(100,200)的像素颜色: {pixel_color}")

        # 4. 图像定位（需要先保存目标图片）
        # 首先截图保存一个目标图片，比如保存为 'target.png'
        # 然后在屏幕上找这个图片

        # 示例：在当前目录查找target.png
        try:
            location = pyautogui.locateOnScreen('target.png', confidence=0.8)
            if location:
                print(f"找到图片，位置: {location}")
                # 点击图片中心
                center = pyautogui.center(location)
                pyautogui.click(center)
        except Exception as e:
            print(f"图片查找失败: {e}")

    def advanced_features(self):
        """高级功能"""
        print("\n=== 高级功能 ===")

        # 1. 消息框
        pyautogui.alert('这是一个警告框！')
        confirm = pyautogui.confirm('确认继续吗？')
        print(f"确认结果: {confirm}")

        # 2. 密码输入
        # password = pyautogui.password('请输入密码:', mask='*')
        # print(f"密码: {password}")

        # 3. 提示输入
        # name = pyautogui.prompt('请输入你的名字:')
        # print(f"名字: {name}")

    def automation_example(self):
        """自动化示例：自动打开记事本并输入内容"""
        print("\n=== 自动化示例：记事本操作 ===")

        # 打开运行窗口
        pyautogui.hotkey('win', 'r')
        time.sleep(0.5)

        # 输入notepad
        pyautogui.write('notepad')
        pyautogui.press('enter')
        time.sleep(1)

        # 输入内容
        content = """这是一个自动化测试：
1. 第一行
2. 第二行
3. 第三行

当前时间: """ + time.strftime('%Y-%m-%d %H:%M:%S')

        pyperclip.copy(content)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1)

        # 保存文件
        pyautogui.hotkey('ctrl', 's')
        time.sleep(1)

        # 输入文件名
        filename = f'automation_test_{time.strftime("%Y%m%d_%H%M%S")}.txt'
        pyautogui.write(filename)
        time.sleep(0.5)

        # 保存
        pyautogui.press('enter')
        time.sleep(1)

        # 关闭记事本
        pyautogui.hotkey('alt', 'f4')

        print(f"已完成自动化操作，文件已保存")

    def run_demo(self):
        """运行演示"""
        print("PyAutoGUI 演示开始")
        print("5秒后开始，请将鼠标移到屏幕左上角停止程序")
        time.sleep(5)

        self.mouse_operations()
        time.sleep(1)

        self.keyboard_operations()
        time.sleep(1)

        # self.screenshot_and_locate()
        # time.sleep(1)

        # self.advanced_features()
        # time.sleep(1)

        # self.automation_example()

        print("\n演示完成！")


# 使用示例
if __name__ == "__main__":
    controller = PyAutoGUIController()
    controller.run_demo()
