import os
import json
from dotenv import load_dotenv

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main():
    os.system('cls' if os.name=='nt' else 'clear')
    load_dotenv()
    
    # 確保這裡拿到的網址是 https://開頭的，不要包含分號等字串
    endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    # 初始化 client
    project_client = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential()
    )
    
    openai_client = project_client.get_openai_client()

    # (工具定義保持不變，略過...)
    tools = [
        {"type": "function", "function": {"name": "next_visible_event", "description": "Get the next visible event.", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}},
        {"type": "function", "function": {"name": "calculate_observation_cost", "description": "Calculate cost.", "parameters": {"type": "object", "properties": {"telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}}, "required": ["telescope_tier", "hours", "priority"]}}},
        {"type": "function", "function": {"name": "generate_observation_report", "description": "Generate report.", "parameters": {"type": "object", "properties": {"event_name": {"type": "string"}, "location": {"type": "string"}, "telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}, "observer_name": {"type": "string"}}, "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"]}}}
    ]

    # 建立 Assistant
    agent = openai_client.beta.assistants.create(
        model=model_deployment,
        name="astronomy-agent",
        instructions="You are an astronomy assistant.",
        tools=tools
    )
    
    # ... (其餘對話迴圈邏輯保持不變)
    thread = openai_client.beta.threads.create()
    print("Agent 已啟動！輸入 'quit' 結束。")
    while True:
        user_input = input("\nUSER: ").strip()
        if user_input.lower() == "quit": break
        openai_client.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_input)
        run = openai_client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=agent.id)
        # ... (工具處理邏輯保持不變)
        messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
        print(f"AGENT: {messages.data[0].content[0].text.value}")

if __name__ == "__main__":
    main()
