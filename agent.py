import os
import json
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
# 我們不手動建立 AzureOpenAI，直接從 project_client 獲取，避免參數錯誤

def main():
    load_dotenv()
    
    # 這是 Azure AI Foundry 官方建議的讀取方式
    # 確保 .env 檔案中有 PROJECT_CONNECTION_STRING
    project_client = AIProjectClient.from_connection_string(
        conn_str=os.environ["PROJECT_CONNECTION_STRING"]
    )
    
    # 透過 project_client 獲取 client，這會自動繼承認證，不會發生 TypeError
    openai_client = project_client.get_openai_client()

    # 以下程式碼保持不變...
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
    
    # ... (其餘與之前相同)
    print("Agent 已啟動！")
    # ...
