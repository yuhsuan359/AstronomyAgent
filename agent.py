import os
import json
from dotenv import load_dotenv

# Add references
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main(): 
    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')

    # Load environment variables
    load_dotenv()
    
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

    if not project_endpoint or not model_deployment:
        print("錯誤: 請確認 .env 檔案中已設定 PROJECT_ENDPOINT 與 MODEL_DEPLOYMENT_NAME")
        return

    # 使用 DefaultAzureCredential，它會自動讀取您 az login 的身分
    credential = DefaultAzureCredential()

    # 連接到 Project Client
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=credential
    )
    
    # 取得 OpenAI client
    openai_client = project_client.get_openai_client()

    # 定義工具的 schema (正確格式)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "next_visible_event",
                "description": "Get the next visible event in a given location.",
                "parameters": {
                    "type": "object",
                    "properties": {"location": {"type": "string", "description": "continent to find the next visible event in"}},
                    "required": ["location"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculate_observation_cost",
                "description": "Calculate the cost of an observation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "telescope_tier": {"type": "string"},
                        "hours": {"type": "number"},
                        "priority": {"type": "string"},
                    },
                    "required": ["telescope_tier", "hours", "priority"],
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "generate_observation_report",
                "description": "Generate a report summarizing an observation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_name": {"type": "string"},
                        "location": {"type": "string"},
                        "telescope_tier": {"type": "string"},
                        "hours": {"type": "number"},
                        "priority": {"type": "string"},
                        "observer_name": {"type": "string"},
                    },
                    "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"],
                }
            }
        }
    ]

    # 建立 Agent
    agent = openai_client.beta.assistants.create(
        model="gpt-4o",
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

        # 發送訊息
        openai_client.beta.threads.messages.create(
            thread_id=thread.id, role="user", content=user_input
        )

        # 執行 Agent
        run = openai_client.beta.threads.runs.create_and_poll(
            thread_id=thread.id, assistant_id=agent.id
        )

        if run.status == 'requires_action':
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                # 執行對應的 function
                if name == "next_visible_event":
                    output = next_visible_event(**args)
                elif name == "calculate_observation_cost":
                    output = calculate_observation_cost(**args)
                elif name == "generate_observation_report":
                    output = generate_observation_report(**args)
                
                tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(output)})
            
            # 送回結果並繼續執行
            run = openai_client.beta.threads.runs.submit_tool_outputs_and_poll(
                thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
            )

        # 顯示結果
        messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
        print(f"AGENT: {messages.data[0].content[0].text.value}")

if __name__ == "__main__":
    main()
