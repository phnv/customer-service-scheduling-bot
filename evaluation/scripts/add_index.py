import re

file_path = "scripts/create_datasets.py"
with open(file_path, "r") as f:
    lines = f.readlines()

sanity_counter = 1
full_counter = 1
in_sanity = False
in_full = False

out_lines = []

for line in lines:
    if "SANITY_RECORDS = [" in line:
        in_sanity = True
        in_full = False
    elif "FULL_RECORDS = [" in line:
        in_full = True
        in_sanity = False
    
    if in_sanity or in_full:
        # Match "tags": {"agent_under_test": "some_agent"},
        # Or "tags": {"agent_under_test": "some_agent"}
        match = re.search(r'("tags":\s*\{"agent_under_test":\s*"[^"]+")(\s*\})', line)
        if match:
            if in_sanity:
                index_str = f"sanity_{sanity_counter:03d}"
                sanity_counter += 1
            else:
                index_str = f"full_{full_counter:03d}"
                full_counter += 1
                
            new_line = line[:match.start(2)] + f', "index": "{index_str}"' + match.group(2) + line[match.end(2):]
            out_lines.append(new_line)
        else:
            out_lines.append(line)
    else:
        out_lines.append(line)

with open(file_path, "w") as f:
    f.writelines(out_lines)
    
print(f"Added {sanity_counter - 1} sanity indices and {full_counter - 1} full indices.")
