## API 契约

### 页面增量放大缩小
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
                "category": "ENLARGE" | "REDUCE", //放大还是缩小
                "value": "20%" //增量变化的幅值
            },
            "businessInfo": {}
        },
    },
    "jump_out_flag": false //是否交给其他BOT处理
}
```

### 页面放大或缩小到目标值
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
                "value": "110%" //目标百分比
            },
            "businessInfo": {}
        },
        "jump_out_flag": false
    }
}
```

### 增加减少表头
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
                "valueType": "NUMERIC" | "STRING", //数值还是字符串
                "value": "用户ID", 1, -1 //表头的名字或者表头的索引，负数意为倒数
            },
            "businessInfo": {}
        },
    },
    "jump_out_flag": false
}
```

### 开通功能
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


### 追问槽位
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


### TW Agent遇到无法处理的意图或决定交给开放域处理
```json
{
    "code": 200,
    "message": "success",
    "answer": { },
    "jump_out_flag": true
}
```


### 发生错误
```json
{
    "code": 500,
    "message": "错误信息",
    "answer": { },
    "jump_out_flag": true
}
```