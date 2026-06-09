import os
import json
from dotenv import load_dotenv

# 引用正確的 Azure AI 庫
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main():
    os.system('cls' if os.name=='nt' else 'clear')
    load_dotenv()
    
    # 這裡的 PROJECT_ENDPOINT 必須是 Azure AI Foundry 的連線字串 (Connection String)
    # 格式範例: <region>.api.azureml.ms;subscriptionId=...;resourceGroup=...;projectId=...
    conn_str = os.getenv("PROJECT_ENDPOINT")
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    if not conn_str:
        print("錯誤: .env 檔案中找不到 PROJECT_ENDPOINT")
        return

    # 1. 使用專案客戶端建立連接
    project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=conn_str
    )
    
    # 2. 正確取得 OpenAI client 的方式 (這會自動處理認證，不需要 credential 參數)
    openai_client = project_client.get_openai_client()

    tools = [
        {"type": "function", "function": {"name": "next_visible_event", "description": "Get the next visible event.", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}},
        {"type": "function", "function": {"name": "calculate_observation_cost", "description": "Calculate cost.", "parameters": {"type": "object", "properties": {"telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}}, "required": ["telescope_tier", "hours", "priority"]}}},
        {"type": "function", "function": {"name": "generate_observation_report", "description": "Generate report.", "parameters": {"type": "object", "properties": {"event_name": {"type": "string"}, "location": {"type": "string"}, "telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}, "observer_name": {"type": "string"}}, "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"]}}}
    ]

    # 3. 建立 Assistant
    agent = openai_client.beta.assistants.create(
        model=deployment_name,
        name="astronomy-agent",
        instructions="You are an astronomy assistant.",
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
