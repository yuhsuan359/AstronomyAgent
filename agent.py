import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential

# 假設 functions.py 已經寫好
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main():
    os.system('cls' if os.name=='nt' else 'clear')
    load_dotenv()
    
    # 1. 直接讀取端點，這是你截圖中那個 https://... 的網址
    endpoint = os.getenv("PROJECT_ENDPOINT")
    deployment = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    # 2. 手動建立 AzureOpenAI Client (最穩定的連線方式)
    # 我們不透過 project_client，直接與部署端點對話
    openai_client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_version="2024-05-01-preview",
        credential=DefaultAzureCredential()
    )

    # 3. 定義工具
    tools = [
        {"type": "function", "function": {"name": "next_visible_event", "description": "Get the next visible event.", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}},
        {"type": "function", "function": {"name": "calculate_observation_cost", "description": "Calculate cost.", "parameters": {"type": "object", "properties": {"telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}}, "required": ["telescope_tier", "hours", "priority"]}}},
        {"type": "function", "function": {"name": "generate_observation_report", "description": "Generate report.", "parameters": {"type": "object", "properties": {"event_name": {"type": "string"}, "location": {"type": "string"}, "telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}, "observer_name": {"type": "string"}}, "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"]}}}
    ]

    # 4. 建立 Assistant
    print(f"正在建立 Assistant，目標部署: {deployment}...")
    try:
        agent = openai_client.beta.assistants.create(
            model=deployment,
            name="astronomy-agent",
            instructions="You are an astronomy assistant.",
            tools=tools
        )
    except Exception as e:
        print(f"\n[關鍵錯誤] 建立失敗: {e}")
        print("如果這裡還是 404，請檢查 Azure AI Foundry 的『模型部署名稱』是否完全等於環境變數中的 MODEL_DEPLOYMENT_NAME。")
        return
    
    # ... (後續對話邏輯保持相同)
    thread = openai_client.beta.threads.create()
    print("Agent 已啟動！")
    
    while True:
        user_input = input("\nUSER: ").strip()
        if user_input.lower() == "quit": break
        openai_client.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_input)
        run = openai_client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=agent.id)
        
        if run.status == 'requires_action':
            # ... (函數呼叫邏輯同前)
            pass
            
        messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
        print(f"AGENT: {messages.data[0].content[0].text.value}")

if __name__ == "__main__":
    main()
