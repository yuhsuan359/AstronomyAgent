import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main():
    # 清除終端機畫面
    os.system('cls' if os.name=='nt' else 'clear')

    # 載入 .env 設定
    load_dotenv()
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    
    if not project_endpoint:
        print("錯誤: 請確認 .env 檔案中已設定 PROJECT_ENDPOINT")
        return

    # 修正 API 端點：移除後綴，保留基礎網址
    base_url = project_endpoint.split('/api/')[0]

    # 直接使用 AzureOpenAI 初始化，確保對接正確的部署名稱 gpt-4.1
    openai_client = AzureOpenAI(
        azure_endpoint=base_url,
        azure_deployment="gpt-4.1",
        api_version="2024-05-01-preview",
        credential=DefaultAzureCredential()
    )

    # 定義工具
    tools = [
        {"type": "function", "function": {
            "name": "next_visible_event",
            "description": "Get the next visible event in a given location.",
            "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}
        }},
        {"type": "function", "function": {
            "name": "calculate_observation_cost",
            "description": "Calculate the cost of an observation.",
            "parameters": {"type": "object", "properties": {"telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}}, "required": ["telescope_tier", "hours", "priority"]}
        }},
        {"type": "function", "function": {
            "name": "generate_observation_report",
            "description": "Generate a report summarizing an observation",
            "parameters": {"type": "object", "properties": {"event_name": {"type": "string"}, "location": {"type": "string"}, "telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}, "observer_name": {"type": "string"}}, "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"]}
        }}
    ]

    # 建立 Agent
    agent = openai_client.beta.assistants.create(
        model="gpt-4.1",
        name="astronomy-agent",
        instructions="You are an astronomy assistant. Use the provided tools to help users.",
        tools=tools
    )
    
    thread = openai_client.beta.threads.create()
    
    print("Agent 已啟動！輸入 'quit' 結束。")
    while True:
        user_input = input("\nUSER: ").strip()
        if user_input.lower() == "quit": break

        openai_client.beta.threads.messages.create(thread_id=thread.id, role="user", content=user_input)
        run = openai_client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=agent.id)

        if run.status == 'requires_action':
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                if name == "next_visible_event": output = next_visible_event(**args)
                elif name == "calculate_observation_cost": output = calculate_observation_cost(**args)
                elif name == "generate_observation_report": output = generate_observation_report(**args)
                tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(output)})
            
            run = openai_client.beta.threads.runs.submit_tool_outputs_and_poll(thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs)

        messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
        print(f"AGENT: {messages.data[0].content[0].text.value}")

if __name__ == "__main__":
    main()
