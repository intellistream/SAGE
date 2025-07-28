### **项目开发环境配置指南**  

#### **1. 安装依赖**  
确保安装 `python-dotenv`：  
```bash
pip install python-dotenv
```

#### **2. 配置环境变量**  
在项目根目录创建 `.env` 文件，并填写你的环境变量，例如：  
```env
# .env 示例
DB_URL="postgresql://user:password@localhost:5432/mydb"
API_KEY="your_api_key_here"
DEBUG="True"
```

#### **3. 代码中加载环境变量**  
在 Python 文件中使用：  
```python
from dotenv import load_dotenv
import os

load_dotenv()  # 加载 .env 文件

db_url = os.getenv("DB_URL")
api_key = os.getenv("API_KEY")
debug = os.getenv("DEBUG", "False").lower() == "true"

print(f"DB_URL: {db_url}")
```

#### **4. 注意事项**  
- **不要提交 `.env` 到 Git！** 确保 `.env` 在 `.gitignore` 里。  
- 如需团队共享变量，请使用 `.env.example` 模板（不含敏感信息）。  

示例 `.gitignore` 条目：  
```
.env
*.env
```  

这样，开发者只需复制 `.env.example` 并填写自己的配置即可。 🚀



