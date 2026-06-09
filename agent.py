import os
import json
import sys
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from functions import next_visible_event, calculate_observation_cost, generate_observation_report

def main():
    sys.stdout.reconfigure(line_buffering=True)
    print("--- 程式開始啟動 (Chat Completions 模式) ---")
    load_dotenv()
    
    endpoint = os.getenv("PROJECT_ENDPOINT")
    deployment_name = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1")

    if not endpoint:
        print("致命錯誤: .env 檔案中找不到 PROJECT_ENDPOINT")
        return

    try:
        project_client = AIProjectClient(endpoint=endpoint, credential=DefaultAzureCredential())
        openai_client = project_client.get_openai_client()

        # 定義工具 (Chat Completion 格式)
        tools = [
            {"type": "function", "function": {"name": "next_visible_event", "description": "Get the next visible event.", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}}},
            {"type": "function", "function": {"name": "calculate_observation_cost", "description": "Calculate cost.", "parameters": {"type": "object", "properties": {"telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}}, "required": ["telescope_tier", "hours", "priority"]}}},
            {"type": "function", "function": {"name": "generate_observation_report", "description": "Generate report.", "parameters": {"type": "object", "properties": {"event_name": {"type": "string"}, "location": {"type": "string"}, "telescope_tier": {"type": "string"}, "hours": {"type": "number"}, "priority": {"type": "string"}, "observer_name": {"type": "string"}}, "required": ["event_name", "location", "telescope_tier", "hours", "priority", "observer_name"]}}}
        ]

        messages = [{"role": "system", "content": "You are an astronomy assistant."}]
        print("--- Agent 已啟動！輸入 'quit' 結束 ---")

        while True:
            user_input = input("\nUSER: ").strip()
            if user_input.lower() == "quit": break

            messages.append({"role": "user", "content": user_input})
            
            # 發送請求
            response = openai_client.chat.completions.create(
                model=deployment_name,
                messages=messages,
                tools=[{"type": "function", "function": t["function"]} for t in tools],
                tool_choice="auto"
            )

            res_message = response.choices[0].message
            messages.append(res_message)

            # 處理 Function Calling
            if res_message.tool_calls:
                for tool_call in res_message.tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    if name == "next_visible_event": result = next_visible_event(**args)
                    elif name == "calculate_observation_cost": result = calculate_observation_cost(**args)
                    elif name == "generate_observation_report": result = generate_observation_report(**args)
                    
                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)})
                
                # 再次發送請求取得最終回答
                final_response = openai_client.chat.completions.create(model=deployment_name, messages=messages)
                answer = final_response.choices[0].message.content
                print(f"AGENT: {answer}")
                messages.append({"role": "assistant", "content": answer})
            else:
                print(f"AGENT: {res_message.content}")

    except Exception as e:
        print(f"\n[發生錯誤]: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
