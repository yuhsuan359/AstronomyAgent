import os
import json
from dotenv import load_dotenv

# Add references
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool
from azure.identity import InteractiveBrowserCredential
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main(): 
    # Clear the console
    os.system('cls' if os.name=='nt' else 'clear')


    # 確認當前 Python 執行的工作目錄
    print(f"DEBUG: 當前工作目錄: {os.getcwd()}")
    
    # 檢查 .env 是否存在於該目錄
    if os.path.exists(".env"):
        print("DEBUG: 找到 .env 檔案了！")
    else:
        print("DEBUG: 找不到 .env 檔案！請檢查檔名是否為 .env")
        return # 檔案沒找到就停止執行
    # Load environment variables
    load_dotenv()
    
    project_endpoint = os.getenv("PROJECT_ENDPOINT")
    model_deployment = os.getenv("MODEL_DEPLOYMENT_NAME")

    if not project_endpoint:
        print("錯誤: 請確認 .env 檔案中已設定 PROJECT_ENDPOINT")
        return

    # 1. 建立認證 (將會跳出瀏覽器登入視窗)
    credential = InteractiveBrowserCredential()

    # 2. 連接到 Project Client (修正初始化方式)
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=credential
    )
    
    # 取得 OpenAI client
    openai_client = project_client.agents.get_openai_client()

    # 定義工具
    event_tool = FunctionTool(
        name="next_visible_event",
        description="Get the next visible event in a given location.",
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "continent to find the next visible event in"},
            },
            "required": ["location"],
        },
    )

    cost_tool = FunctionTool(
        name="calculate_observation_cost",
        description="Calculate the cost of an observation.",
        parameters={
            "type": "object",
            "properties": {
                "telescope_tier": {"type": "string"},
                "hours": {"type": "number"},
                "priority": {"type": "string"},
            },
            "required": ["telescope_tier", "hours", "priority"],
        },
    )

    report_tool = FunctionTool(
        name="generate_observation_report",
        description="Generate a report summarizing an observation",
        parameters={
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
        },
    )

    # 建立 Agent
    agent = project_client.agents.create_agent(
        model=model_deployment,
        name="astronomy-agent",
        instructions="You are an astronomy assistant. Use tools to help users.",
        tools=[event_tool, cost_tool, report_tool],
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
            # 處理工具呼叫
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                if name == "next_visible_event":
                    output = next_visible_event(**args)
                elif name == "calculate_observation_cost":
                    output = calculate_observation_cost(**args)
                elif name == "generate_observation_report":
                    output = generate_observation_report(**args)
                
                tool_outputs.append({"tool_call_id": tool_call.id, "output": json.dumps(output)})
            
            # 送回結果
            openai_client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread.id, run_id=run.id, tool_outputs=tool_outputs
            )
            # 等待完成
            run = openai_client.beta.threads.runs.poll(thread_id=thread.id, run_id=run.id)

        # 顯示結果
        messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
        if messages.data:
            print(f"AGENT: {messages.data[0].content[0].text.value}")

if __name__ == "__main__":
    main()
