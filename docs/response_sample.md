## API 契约

### 执行动作: 页面增量放大缩小
```json
{
    "code": 200,
    "message": "success",
    "answer": {
        "messageType": "FORMAT_INTELLIGENT_EXEC",
        "content": {
            "businessId": "twAgentExec", //待网银输入，业务类型
            "operateType": "PAGE_RESIZE_INCREMENT", //触发的动作名称
            "operateSlots": {
                "category": "INCREASE" | "DECREASE", //放大还是缩小
                "value": "20" //增量变化的幅值，10的倍数，默认值为10，通过YAML文件配置
            },
            "businessInfo": {
                "instruction": "放大/缩小页面字体xx%"
            }
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
            "businessId": "twAgentExec",
            "operateType": "PAGE_RESIZE_INCREMENT", //触发的动作名称
            "operateSlots": {
                "category": "INCREASE", //放大还是缩小
                "value": "10", //默认值为10，通过YAML文件配置
            },
            "businessInfo": {
                "instruction": "放大/缩小页面字体xx%"
            }
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
            "businessId": "twAgentExec",
            "operateType": "PAGE_RESIZE_TARGET",
            "operateSlots": {
                "value": "110" //目标百分比，可选参数，如果没有该字段，触发UI兜底「如缩放按钮的高亮」
            },
            "businessInfo": {
                "instruction": "放大页面字体xx到%"
            }
        },},
  
    "jump_out_flag": false
    }
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
            "businessId": "twAgentExec",
            "operateType": "PAGE_RESIZE_TARGET", //触发的动作名称
            "operateSlots": {
                "value": "", //默认值为10，通过YAML文件配置
            },
            "businessInfo": {
                "instruction": ""
            }
        },
    },
    "jump_out_flag": false //是否交给其他BOT处理
}
```


### 执行动作: 增加删除表头（category、valueType和value中有任意一个字段为空字符串的时候，触发UI兜底「如弹出表头列表供用户勾选」）
```json
{
    "code": 200,
    "message": "success",
    "answer": {
        "messageType": "FORMAT_INTELLIGENT_EXEC",
        "content": {
            "businessId": "twAgentExec",
            "operateType": "ADJUST_HEADER",
            "operateSlots": {
                "category": "ADD" | "REMOVE", //增加或者删除
                "valueType": "INDEX" | "NAME", //数值还是字符串 INDEX只会出现在删除列的时候
                "value": "用户ID" | 1 | -1 //表头的名字或者表头的索引，负数意为倒数第n
            },
            "businessInfo": {
                "instruction": "增加/删减表头xx"
            }
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
            "businessId": "twAgentExec",
            "operateType": "ACTIVATE_FUNCTION",
            "operateSlots": {
                "value": "发票云" //「功能名」或者「功能代码」。用户在多轮引导下没有提及功能名称或者代码，“value”传空字符串，网银前端跳转到开通功能的总页面。此外，推荐：网银前端没有成功匹配到功能名称/代码，也采用跳转到开通功能总页面的兜底。如果功能代码不在可在线开通的列表中，网银前端可在页面上进行提示线下办理）
            },
            "businessInfo": {
                "instruction": "开通功能xx"
            }
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