import os

old_file = "agent_verbose_logs.txt"
new_file = "agent_verbose_logs_fixed.txt"

with open(old_file, "r", encoding="utf-16le", errors="replace") as f:
    content = f.read()

with open(new_file, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully converted. New file is {new_file}")

with open("agent_verbose_logs_preview.txt", "w", encoding="utf-8") as f:
    f.write(content[:2000]) # First 2000 chars for preview
