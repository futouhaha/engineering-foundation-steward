"""Check the visible sections of a consultation supplied on stdin. Never reads project files."""
import re
import sys

HEADINGS = (
    '## 用户方案',
    '### 01 项目画像与信息充分性',
    '### 02 工程基建全景与适配结果',
    '### 03 推荐建设方案与选择理由',
    '### 04 工程机制联动与实际使用方式',
    '### 05 工程成长与复评条件',
    '## 共同决定条款',
    '### 06 本次批准范围、验收与退出',
    '## Main Brief',
)
LIMIT = 256 * 1024


def check(report):
    sections = []
    nonempty = []
    anchors = {}
    fence = None
    for line in report.splitlines():
        stripped = line.strip()
        marker = re.match(r"^(`{3,}|~{3,})(.*)$", stripped)
        if marker:
            run, tail = marker.groups()
            if fence is None:
                fence = run
            elif run.startswith(fence) and not tail.strip():
                fence = None
            continue
        if fence:
            continue
        if stripped.startswith(("## ", "### ")):
            sections.append(stripped)
            nonempty.append(False)
        elif nonempty and stripped and not stripped.startswith("#"):
            nonempty[-1] = True
            if sections[-1] == HEADINGS[-2]:
                # A bold field label may end at a colon or at a visible space.
                plain = stripped.removeprefix("- ")
                label = re.match(r"^\*\*(持续机制|下次复验)\*\*\s+(.+)$", plain)
                if label:
                    key, value = label.groups()
                else:
                    key, sep, value = plain.replace("**", "").partition("：")
                    if not sep or key not in ("持续机制", "下次复验"):
                        continue
                if key in anchors or not value.strip():
                    return False
                anchors[key] = value.strip()
    return (tuple(sections) == HEADINGS
            and all(body for title, body in zip(sections, nonempty)
                    if title.startswith("### ") or title == "## Main Brief")
            and len(set(anchors.values())) == 2)


def main():
    data = sys.stdin.buffer.read(LIMIT + 1)
    if len(data) <= LIMIT:
        try:
            if check(data.decode("utf-8")):
                print("结构完整；语义、批准、实施与验证需另核。")
                return 0
        except UnicodeDecodeError:
            pass
    print("无法确认交付结构：检查 UTF-8、长度、章节顺序、正文及共同条款的持续机制和下次复验。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
