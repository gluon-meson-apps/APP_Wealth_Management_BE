## API 契约

### 执行动作: 页面增量放大缩小
```json
{
    "code": 200,
    "message": "success",
    "answer": {
        "messageType": "FORMAT_INTELLIGENT_EXEC",
        "content": {
            "businessId": "N35010Operate", //待网银输入
            "operateType": "PAGE_RESIZE_INCREMENT", //触发的动作名称
            "operateSlots": {
                "category": "INCREASE" | "DECREASE", //放大还是缩小
                "value": "20" //增量变化的幅值，可选参数，如果没有该字段，触发UI兜底
            },
            "businessInfo": {}
        },
    },
    "jump_out_flag": false //融合引擎需要，是否交给其他BOT处理
}
```

用户没有输入明确的幅值
```json
{
    "code": 200,
    "message": "success",
    "answer": {
        "messageType": "FORMAT_INTELLIGENT_EXEC",
        "content": {
            "businessId": "N35010Operate",
            "operateType": "PAGE_RESIZE_INCREMENT", //触发的动作名称
            "operateSlots": {
                "category": "INCREASE", //放大还是缩小
                "value": "10", //默认10%，可以通过YAML配置
            },
            "businessInfo": {}
        },
    },
    "jump_out_flag": false //是否交给其他BOT处理
}
```


### 执行动作: 页面放大或缩小到目标值
```json
{
    "code": 200,
    "message": "success",
    "answer": {
        "messageType": "FORMAT_INTELLIGENT_EXEC",
        "content": {
            "businessId": "N35010Operate",
            "operateType": "PAGE_RESIZE_TARGET",
            "operateSlots": {
                "value": "110" //目标百分比，可选参数，如果没有该字段，触发UI兜底
            },
            "businessInfo": {}
        },
        "jump_out_flag": false
    }
}
```


### 执行动作: 增加减少表头
```json
{
    "code": 200,
    "message": "success",
    "answer": {
        "messageType": "FORMAT_INTELLIGENT_EXEC",
        "content": {
            "businessId": "N35010Operate",
            "operateType": "HEADER_ADJUSTMENT",
            "operateSlots": {
                "category": "ADD" | "REMOVE", //增加或者减少
                "valueType": "INDEX" | "NAME", //数值还是字符串，可选参数，如果没有该字段，触发UI兜底
                "value": "用户ID" | 1 | -1 //表头的名字或者表头的索引，负数意为倒数第n，可选参数
            },
            "businessInfo": {}
        },
    },
    "jump_out_flag": false
}
```


### 执行动作: 开通功能
```json
{
    "code": 200,
    "message": "success",
    "answer": {
        "messageType": "FORMAT_INTELLIGENT_EXEC",
        "content": {
            "businessId": "N35010Operate",
            "operateType": "ACTIVATE_FUNCTION",
            "operateSlots": {
                "value": "发票云" //功能名，可选参数
            },
            "businessInfo": {}
        },
    },
    "jump_out_flag": false
}
```


### 回复文本: 追问槽位
```json
{
    "code": 200,
    "message": "success",
    "answer": {
        "messageType": "FORMAT_TEXT",
        "content": "请问您要开通什么功能",
    },
    "jump_out_flag": false
}
```


### 其他: TW Agent遇到无法处理的意图或其他决定交给开放域处理的情况
```json
{
    "code": 200,
    "message": "success",
    "answer": { },
    "jump_out_flag": true
}
```


### 其他: Agent 中发生错误
```json
{
    "code": 500,
    "message": "错误信息",
    "answer": { },
    "jump_out_flag": true
}
```