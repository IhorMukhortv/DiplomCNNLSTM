import os

log_path = r"C:\Users\igorl\.gemini\antigravity\brain\c42e4933-eed1-40e4-ad53-e3a579bd0dff\.system_generated\logs\transcript.jsonl"
if not os.path.exists(log_path):
    print("Logs not found.")
    exit(1)

with open(log_path, "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, 1):
        if "project_structure.png" in line:
            # check if it is part of a tool call or response
            if "tool_calls" in line or "output" in line or "ReplacementContent" in line or "CodeContent" in line:
                print(f"Line {idx}:")
                pos = line.find("project_structure.png")
                start = max(0, pos - 150)
                end = min(len(line), pos + 250)
                print(line[start:end])
                print("="*60)
