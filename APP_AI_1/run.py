"""启动脚本"""
import uvicorn
from app_ai.config import config

if __name__ == "__main__":
    print(f"启动: http://{config.HOST}:{config.PORT}")
    # 重点：后面是 :app 不是 :app_ai
    uvicorn.run("app_ai.main:app", host=config.HOST, port=config.PORT, reload=False)