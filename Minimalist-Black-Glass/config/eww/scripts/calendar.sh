#!/usr/bin/env bash
# eww calendar widget — current month grid, today highlighted via pango markup
python3 - <<'EOF'
import datetime, calendar
today = datetime.date.today()
y, m = today.year, today.month
wday0 = datetime.date(y, m, 1).weekday()
cm = calendar.monthrange(y, m)[1]
cellno = wday0 + today.day - 1

lines = ["      %s %d" % (calendar.month_abbr[m].upper(), y)]
header = " ".join(["MO","TU","WE","TH","FR","SA","SU"])
lines.append(" " * max(0, (20 - len(header)) // 2) + header)  # 7*2 + 6 = 20 wide

cells = ["  "] * wday0
for d in range(1, cm + 1):
    cells.append("%2d" % d)
while len(cells) % 7:
    cells.append("  ")

for i in range(0, len(cells), 7):
    row = cells[i:i+7]
    if i <= cellno < i + 7:
        row[cellno - i] = '<span underline="double" weight="bold">%02d</span>' % today.day
    lines.append(" ".join(row))

print("\n".join(lines))
EOF