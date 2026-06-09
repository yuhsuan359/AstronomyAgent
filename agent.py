import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential

def main():
    os.system('cls' if os.name=='nt' else 'clear')
    load_dotenv()
    
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    if not project_endpoint:
        print("錯誤: .env 缺少 PROJECT_ENDPOINT")
        return

    # 使用基礎網址初始化
    base_url = project_endpoint.split('/api/')[0]
    openai_client = AzureOpenAI(
        azure_endpoint=base_url,
        azure_deployment="gpt-4.1",
        api_version="2024-05-01-preview",
        credential=DefaultAzureCredential()
    )

    print("Agent 已啟動 (Chat 模式)！輸入 'quit' 結束。")
    # 直接使用 Chat Completions API，避開複雜的 Assistants API
    messages = [{"role": "system", "content": "You are a helpful astronomy assistant."}]

    while True:
        user_input = input("\nUSER: ").strip()
        if user_input.lower() == "quit": break

        messages.append({"role": "user", "content": user_input})
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=messages
            )
            reply = response.choices[0].message.content
            print(f"AGENT: {reply}")
            messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            print(f"發生錯誤: {e}")

if __name__ == "__main__":
    main()
