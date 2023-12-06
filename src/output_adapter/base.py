import re
from gm_logger import get_logger

logger = get_logger()

def chinese_to_arabic(chinese):
    # 编写转换函数，将汉字数字转换为阿拉伯数字
    # 这里可以根据需要扩展转换范围
    chinese_dict = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
    arabic_number = 0
    temp = 0
    has_chinese_num = False
    for char in chinese:
        if char in chinese_dict:
            temp = chinese_dict[char]
            has_chinese_num = True
        else:
            if char == '十':
                has_chinese_num = True
                temp *= 10
                arabic_number += temp
                temp = 0
            elif char == '百':
                has_chinese_num = True
                temp *= 10
                arabic_number += temp
                temp = 0
    
    arabic_number += temp
    if has_chinese_num:
        return arabic_number
    else:
        return None


class OutputAdapter:
    def process_output(self, output: str) -> str:
        raise NotImplementedError()


class BaseOutputAdapter(OutputAdapter):
    def process_output(self, output: str) -> str:
        return output

    def normalize_percentage(self, text):
        # 定义正则表达式模式来匹配不同形式的百分比文本
        patterns = [
            r'(\d+)%',            # 匹配数字%形式，例如：20%
            r'百分之(\d+)',       # 匹配“百分之”加数字形式，例如：百分之20
            r'百分之([\u4e00-\u9fff]+)',  # 匹配“百分之”加汉字数字形式，例如：百分之二十
            r'%(\d+)'             # 匹配%加数字形式，例如：%20
        ]

        # 遍历模式进行匹配
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                # 如果匹配成功，先尝试对汉字数字进行转换
                chinese_number = match.group(1)
                arabic_number = chinese_to_arabic(chinese_number)
                
                if arabic_number is not None:
                    return f"{arabic_number}%"
                else:
                    # 如果没有匹配到汉字数字，直接返回匹配到的内容
                    return f"{match.group(1)}%"

        # 如果没有匹配成功，打印警告并返回空字符串
        print("警告：未能识别百分比文本格式！")
        return ""