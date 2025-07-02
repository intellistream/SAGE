# file sage/core/sage_memory/operator_test/structure_mem_demo/img/img_input.py
# python -m sage.core.sage_memory.operator_test.structure_mem_demo.img.img_input

from sage.api.model import apply_generator_model, apply_embedding_model

food = [{"user_id": "u001", "timestamp": "2025-05-16T08:00:00", "caption": "早餐是一个煎蛋三明治和无糖豆浆，快速搞定。", "metadata": {"meal_type": "breakfast", "calorie": 342}},
{"user_id": "u001", "timestamp": "2025-05-16T12:30:00", "caption": "今天中午简单做了青菜炒蛋配米饭。", "metadata": {"meal_type": "lunch", "calorie": 755}},
{"user_id": "u001", "timestamp": "2025-05-16T18:30:00", "caption": "试了低卡便当：鸡胸肉+藜麦+胡萝卜。", "metadata": {"meal_type": "dinner", "calorie": 628}},
{"user_id": "u001", "timestamp": "2025-05-17T08:00:00", "caption": "早餐喝了蛋白粉奶昔，省时间还顶饱。", "metadata": {"meal_type": "breakfast", "calorie": 269}},
{"user_id": "u001", "timestamp": "2025-05-17T12:00:00", "caption": "外卖点了烤鱼，味道重但挺过瘾。", "metadata": {"meal_type": "lunch", "calorie": 635}},
{"user_id": "u001", "timestamp": "2025-05-17T18:30:00", "caption": "晚上没太饿，吃了点水果+酸奶。", "metadata": {"meal_type": "dinner", "calorie": 612}},
{"user_id": "u001", "timestamp": "2025-05-18T08:00:00", "caption": "早餐是一个煎蛋三明治和无糖豆浆，快速搞定。", "metadata": {"meal_type": "breakfast", "calorie": 391}},
{"user_id": "u001", "timestamp": "2025-05-18T12:30:00", "caption": "外卖点了烤鱼，味道重但挺过瘾。", "metadata": {"meal_type": "lunch", "calorie": 688}},
{"user_id": "u001", "timestamp": "2025-05-18T18:00:00", "caption": "试了低卡便当：鸡胸肉+藜麦+胡萝卜。", "metadata": {"meal_type": "dinner", "calorie": 549}},
{"user_id": "u001", "timestamp": "2025-05-19T08:30:00", "caption": "今天早上试了牛奶麦片，味道还可以。", "metadata": {"meal_type": "breakfast", "calorie": 339}},
{"user_id": "u001", "timestamp": "2025-05-19T12:30:00", "caption": "吃了红烧鸡块+西兰花+米饭，挺健康的。", "metadata": {"meal_type": "lunch", "calorie": 619}},
{"user_id": "u001", "timestamp": "2025-05-19T18:30:00", "caption": "晚餐是一碗鸡丝面+凉拌黄瓜，轻食一下。", "metadata": {"meal_type": "dinner", "calorie": 514}},
{"user_id": "u001", "timestamp": "2025-05-20T08:00:00", "caption": "早餐是一个煎蛋三明治和无糖豆浆，快速搞定。", "metadata": {"meal_type": "breakfast", "calorie": 324}},
{"user_id": "u001", "timestamp": "2025-05-20T12:00:00", "caption": "今天中午简单做了青菜炒蛋配米饭。", "metadata": {"meal_type": "lunch", "calorie": 560}},
{"user_id": "u001", "timestamp": "2025-05-20T18:30:00", "caption": "做了西红柿炒蛋和小炒肉配米饭。", "metadata": {"meal_type": "dinner", "calorie": 636}},
{"user_id": "u001", "timestamp": "2025-05-21T08:00:00", "caption": "今早吃了燕麦粥配鸡蛋，清淡但挺有能量的。", "metadata": {"meal_type": "breakfast", "calorie": 295}},
{"user_id": "u001", "timestamp": "2025-05-21T12:30:00", "caption": "吃了红烧鸡块+西兰花+米饭，挺健康的。", "metadata": {"meal_type": "lunch", "calorie": 536}},
{"user_id": "u001", "timestamp": "2025-05-21T18:00:00", "caption": "晚上没太饿，吃了点水果+酸奶。", "metadata": {"meal_type": "dinner", "calorie": 671}},
{"user_id": "u001", "timestamp": "2025-05-22T08:00:00", "caption": "早餐喝了蛋白粉奶昔，省时间还顶饱。", "metadata": {"meal_type": "breakfast", "calorie": 373}},
{"user_id": "u001", "timestamp": "2025-05-22T12:00:00", "caption": "今天中午简单做了青菜炒蛋配米饭。", "metadata": {"meal_type": "lunch", "calorie": 695}},
{"user_id": "u001", "timestamp": "2025-05-22T18:30:00", "caption": "晚上没太饿，吃了点水果+酸奶。", "metadata": {"meal_type": "dinner", "calorie": 544}},
{"user_id": "u001", "timestamp": "2025-05-23T08:30:00", "caption": "早餐是一个煎蛋三明治和无糖豆浆，快速搞定。", "metadata": {"meal_type": "breakfast", "calorie": 271}},
{"user_id": "u001", "timestamp": "2025-05-23T12:30:00", "caption": "吃了红烧鸡块+西兰花+米饭，挺健康的。", "metadata": {"meal_type": "lunch", "calorie": 788}},
{"user_id": "u001", "timestamp": "2025-05-23T18:00:00", "caption": "做了西红柿炒蛋和小炒肉配米饭。", "metadata": {"meal_type": "dinner", "calorie": 520}},
{"user_id": "u001", "timestamp": "2025-05-24T08:00:00", "caption": "早餐是一个煎蛋三明治和无糖豆浆，快速搞定。", "metadata": {"meal_type": "breakfast", "calorie": 300}},
{"user_id": "u001", "timestamp": "2025-05-24T12:00:00", "caption": "外卖点了烤鱼，味道重但挺过瘾。", "metadata": {"meal_type": "lunch", "calorie": 719}},
{"user_id": "u001", "timestamp": "2025-05-24T18:00:00", "caption": "晚上没太饿，吃了点水果+酸奶。", "metadata": {"meal_type": "dinner", "calorie": 664}},
{"user_id": "u001", "timestamp": "2025-05-25T08:00:00", "caption": "今天早上试了牛奶麦片，味道还可以。", "metadata": {"meal_type": "breakfast", "calorie": 255}},
{"user_id": "u001", "timestamp": "2025-05-25T12:30:00", "caption": "外卖点了烤鱼，味道重但挺过瘾。", "metadata": {"meal_type": "lunch", "calorie": 606}},
{"user_id": "u001", "timestamp": "2025-05-25T18:00:00", "caption": "做了西红柿炒蛋和小炒肉配米饭。", "metadata": {"meal_type": "dinner", "calorie": 621}},
{"user_id": "u001", "timestamp": "2025-05-26T08:30:00", "caption": "早餐喝了蛋白粉奶昔，省时间还顶饱。", "metadata": {"meal_type": "breakfast", "calorie": 344}},
{"user_id": "u001", "timestamp": "2025-05-26T12:30:00", "caption": "午餐吃了麻辣烫，虽然油了点但很满足。", "metadata": {"meal_type": "lunch", "calorie": 771}},
{"user_id": "u001", "timestamp": "2025-05-26T18:00:00", "caption": "试了低卡便当：鸡胸肉+藜麦+胡萝卜。", "metadata": {"meal_type": "dinner", "calorie": 403}},
{"user_id": "u001", "timestamp": "2025-05-27T08:30:00", "caption": "今天早上试了牛奶麦片，味道还可以。", "metadata": {"meal_type": "breakfast", "calorie": 261}},
{"user_id": "u001", "timestamp": "2025-05-27T12:30:00", "caption": "午餐吃了麻辣烫，虽然油了点但很满足。", "metadata": {"meal_type": "lunch", "calorie": 665}},
{"user_id": "u001", "timestamp": "2025-05-27T18:00:00", "caption": "试了低卡便当：鸡胸肉+藜麦+胡萝卜。", "metadata": {"meal_type": "dinner", "calorie": 524}},
{"user_id": "u001", "timestamp": "2025-05-28T08:30:00", "caption": "早餐是一个煎蛋三明治和无糖豆浆，快速搞定。", "metadata": {"meal_type": "breakfast", "calorie": 283}},
{"user_id": "u001", "timestamp": "2025-05-28T12:00:00", "caption": "今天中午简单做了青菜炒蛋配米饭。", "metadata": {"meal_type": "lunch", "calorie": 571}},
{"user_id": "u001", "timestamp": "2025-05-28T18:30:00", "caption": "晚饭随便煮了点意面，懒得出门了。", "metadata": {"meal_type": "dinner", "calorie": 582}},
{"user_id": "u001", "timestamp": "2025-05-29T08:30:00", "caption": "早餐是一个煎蛋三明治和无糖豆浆，快速搞定。", "metadata": {"meal_type": "breakfast", "calorie": 326}},
{"user_id": "u001", "timestamp": "2025-05-29T12:30:00", "caption": "外卖点了烤鱼，味道重但挺过瘾。", "metadata": {"meal_type": "lunch", "calorie": 708}},
{"user_id": "u001", "timestamp": "2025-05-29T18:00:00", "caption": "晚餐是一碗鸡丝面+凉拌黄瓜，轻食一下。", "metadata": {"meal_type": "dinner", "calorie": 544}}]
# food = {"user_id": "u001", "timestamp": "2025-05-29T12:00:00", "text": "晨跑26分钟，虽然有点累，但跑完后整个人有点疲惫但很开心，感觉可以继续坚持这个习惯。", "metadata": {"activity_type": "running", "duration_min": 26}}
sport = [{"user_id": "u001", "timestamp": "2025-05-16T14:00:00", "text": "晚上去健身房练了27分钟力量训练，练了背部，整个人特别满足。", "metadata": {"activity_type": "strength_training", "duration_min": 27}},
{"user_id": "u001", "timestamp": "2025-05-21T13:30:00", "text": "今天早上我在城市绿道跑步了58分钟，天气晴朗，出了一身汗，感觉精力充沛。", "metadata": {"activity_type": "running", "duration_min": 58}},
{"user_id": "u001", "timestamp": "2025-05-22T10:30:00", "text": "今天的骑行非常顺利，尤其是在公园这一段，配合了音乐感觉更有动力。", "metadata": {"activity_type": "cycling", "duration_min": 41}},
{"user_id": "u001", "timestamp": "2025-05-22T15:00:00", "text": "今天的骑行非常疲惫，尤其是在城市绿道这一段，感觉可以继续坚持这个习惯。", "metadata": {"activity_type": "cycling", "duration_min": 36}},
{"user_id": "u001", "timestamp": "2025-05-23T07:00:00", "text": "今天在健身房专注训练腿部，练了56分钟，希望明天能继续。", "metadata": {"activity_type": "strength_training", "duration_min": 56}},
{"user_id": "u001", "timestamp": "2025-05-27T13:00:00", "text": "早上散步放松了一下，走了49分钟，顺便整理了下思绪。", "metadata": {"activity_type": "walking", "duration_min": 49}},
{"user_id": "u001", "timestamp": "2025-05-28T07:30:00", "text": "早上散步放松了一下，走了32分钟，感觉可以继续坚持这个习惯。", "metadata": {"activity_type": "walking", "duration_min": 32}},
{"user_id": "u001", "timestamp": "2025-05-29T12:00:00", "text": "晨跑26分钟，虽然有点累，但跑完后整个人有点疲惫但很开心，感觉可以继续坚持这个习惯。", "metadata": {"activity_type": "running", "duration_min": 26}}
]
health = [{"user_id": "u001", "timestamp": "2025-05-16T17:30:00", "text": "本周血压偏低，有点轻微头痛，可能和没休息好有关。"},
{"user_id": "u001", "timestamp": "2025-05-17T12:30:00", "text": "最近感觉精神不太集中，医生建议我保持稳定作息，要注意保持情绪平稳。"},
{"user_id": "u001", "timestamp": "2025-05-18T15:30:00", "text": "最近感觉睡眠不好，医生建议我保持稳定作息，要注意饮食清淡。"},
{"user_id": "u001", "timestamp": "2025-05-19T18:00:00", "text": "今天复诊时医生特别强调规律服药，还建议我保持锻炼习惯。"},
{"user_id": "u001", "timestamp": "2025-05-20T14:00:00", "text": "本周血压偏低，有点有些乏力，可能和没休息好有关。"},
{"user_id": "u001", "timestamp": "2025-05-21T17:00:00", "text": "本周血压正常，有点轻微头痛，可能和没休息好有关。"},
{"user_id": "u001", "timestamp": "2025-05-22T10:00:00", "text": "身体状态一般，状态还行，就是有点累，准备这几天安排下次体检。"},
{"user_id": "u001", "timestamp": "2025-05-23T18:00:00", "text": "今天复诊时医生特别强调多补充蔬菜，还建议我记录饮食。"},
{"user_id": "u001", "timestamp": "2025-05-25T17:30:00", "text": "身体状态一般，最近心情也有点起伏，准备这几天调整锻炼计划。"},
{"user_id": "u001", "timestamp": "2025-05-26T11:30:00", "text": "慢性病监测：高血压，当前状态波动中，医生说建议注意饮食结构。"},
{"user_id": "u001", "timestamp": "2025-05-27T18:30:00", "text": "身体状态一般，身体沉重感加剧了，准备这几天安排下次体检。"},
{"user_id": "u001", "timestamp": "2025-05-28T10:30:00", "text": "本周血压忽高忽低，有点没太大感觉，可能和天气变化有关。"},
{"user_id": "u001", "timestamp": "2025-05-29T13:00:00", "text": "今天复诊时医生特别强调不要暴饮暴食，还建议我每周做一次血液检查。"}]

api_key = "sk-b21a67cf99d14ead9d1c5bf8c2eb90ef"
# prompt=[{"role":"user","content":"who are you"}]
prompt = [
        {"role": "system", "content": f"你是一个贴心的用户健康助手，你将参考用户运动信息{sport}，历史饮食信息{food}，历史健康信息{health}，来回答用户提问"},
        {"role":"user",
           "content": [
            {"type": "text", "text": "图片是用户早上的饮食，请问用户今天(2025-5-30)还可以摄取多少卡路里的食物？"},
            {"type": "image_url",
             "image_url": {"url": "https://img1.baidu.com/it/u=2343437634,2142792307&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=1067"}}
            ]}
        ]
model = apply_generator_model("openai", model_name="qwen-vl-max", base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", api_key=api_key, seed=42)
response=model.generate(prompt)
print(response)
