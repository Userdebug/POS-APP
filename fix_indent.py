"""Fix indentation of product_info_panel.py."""

path = "ui/components/product_info_panel.py"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
i = 0
n = len(lines)
while i < n:
    line = lines[i]
    stripped = line.lstrip()
    leading = len(line) - len(stripped)
    if stripped.startswith("def "):
        if leading > 4:
            delta = leading - 4
            new_lines.append(" " * 4 + stripped)
            i += 1
            while i < n:
                subline = lines[i]
                substripped = subline.lstrip()
                if substripped.startswith("def "):
                    break
                if subline.strip() == "":
                    new_lines.append(subline)
                else:
                    sublead = len(subline) - len(substripped)
                    if sublead >= delta:
                        new_line = " " * (sublead - delta) + substripped
                    else:
                        new_line = subline
                    new_lines.append(new_line)
                i += 1
            continue
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)
    i += 1

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Indentation fixed.")
