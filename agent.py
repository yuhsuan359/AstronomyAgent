import os
import json
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main():
    os.system('cls' if os.name=='nt' else 'clear')
    load_dotenv()
    
    # 1. 確保 Connection String 正確
    conn_str = os.getenv("PROJECT_ENDPOINT")
    if not conn_str:
        print("錯誤: .env 找不到 PROJECT_ENDPOINT")
        return

    # 2. 初始化 Client
    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=conn_str
    )
    
    # 3. 關鍵修正：直接取得 OpenAI Client，並確保指定正確的 API 版本
    openai_client = project_client.get_openai_client(api_version="2024-05-01-preview")

    # 4. 建立 Assistant 時，明確使用部署名稱
    # 如果還是報 404，請檢查 Azure AI Foundry > Models > Deployments 中該模型的 Name
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")
    
    tools = [
        {"type": "function", "function": {"name": "next_visible_event", "description": "Get the next visible event in a given location.", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}},
        {"type": "function", "function": {"name": "calculate_observation_cost", "description": "Calculate the cost of an observation.", "parameters": {"type": "object", "properties": {"telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}}, "required": ["telescope_tier", "hours", "priority"]}}},
        {"type": "function", "function": {"name": "generate_observation_report", "description": "Generate a report summarizing an observation", "parameters": {"type": "object", "properties": {"event_name": {"type": "string"}, "location": {"type": "string"}, "telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}, "observer_name": {"type": "string"}}, "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"]}}}
    ]

    print(f"正在連線至部署: {deployment_name} ...")
    
    try:
        agent = openai_client.beta.assistants.create(
            model=deployment_name, 
            name="astronomy-agent",
            instructions="You are an astronomy assistant.",
            tools=tools
        )
    except Exception as e:
        print(f"\n[致命錯誤] 建立 Assistant 失敗: {e}")
        print("提示: 請檢查 Azure AI Foundry > Models > Deployments 中的模型名稱是否為 'gpt-4.1'")
        return
    
    thread = openai_client.beta.threads.create()
    
    print("Agent 已啟動！")
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
                
                # 執行函數
                result = None
                if name == "next_visible_event": result = next_visible_event(**args)
                elif name == "calculate_observation_cost": result = calculate_observation_cost(**args)
                elif name == "generate_observation_report": result = generate_observation_report(**args)
                
                tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(result)})
            
            run = openai_client.beta.threads.runs.submit_tool_outputs_and_poll(thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs)

        messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
        print(f"AGENT: {messages.data[0].content[0].text.value}")

if __name__ == "__main__":
    main()
