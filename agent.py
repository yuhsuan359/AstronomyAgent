import os
import json
from dotenv import load_dotenv

# 使用原生的 Azure AI Projects SDK
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main():
    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')

    # Load environment variables
    load_dotenv()
    
    # 請確保 .env 中的 PROJECT_ENDPOINT 是完整的 Connection String
    # 格式如: "eastus.api.azureml.ms;subscriptionId=...;resourceGroup=...;projectId=..."
    project_connection_string = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    if not project_connection_string:
        print("錯誤: 請確認 .env 檔案中已設定 PROJECT_ENDPOINT (請使用 Connection String)")
        return

    # 使用 DefaultAzureCredential，它會自動抓取你 az login 的登入狀態
    credential = DefaultAzureCredential()

    # 使用 Connection String 初始化，這是最穩定、最能解決 404 的連線方式
    project_client = AIProjectClient.from_connection_string(
        credential=credential,
        conn_str=project_connection_string
    )
    
    # 取得 OpenAI client
    openai_client = project_client.get_openai_client()

    # 定義工具
    tools = [
        {
            "type": "function", 
            "function": {
                "name": "next_visible_event",
                "description": "Get the next visible event in a given location.",
                "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}
            }
        },
        {
            "type": "function", 
            "function": {
                "name": "calculate_observation_cost",
                "description": "Calculate the cost of an observation.",
                "parameters": {"type": "object", "properties": {"telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}}, "required": ["telescope_tier", "hours", "priority"]}
            }
        },
        {
            "type": "function", 
            "function": {
                "name": "generate_observation_report",
                "description": "Generate a report summarizing an observation",
                "parameters": {"type": "object", "properties": {"event_name": {"type": "string"}, "location": {"type": "string"}, "telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}, "observer_name": {"type": "string"}}, "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"]}
            }
        }
    ]

    # 建立 Agent
    agent = openai_client.beta.assistants.create(
        model=model_deployment,
        name="astronomy-agent",
        instructions="You are an astronomy assistant. Use the provided tools to help users.",
        tools=tools
    )
    
    # 建立對話 Thread
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
        if messages.data:
            print(f"AGENT: {messages.data[0].content[0].text.value}")

if __name__ == "__main__":
    main()
