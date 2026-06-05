"""
内容清洗模块 - 将 HTML 正文转换为纯文本
"""
import re
import html
from bs4 import BeautifulSoup


def html_to_text(html_content: str) -> str:
    """
    将包含 HTML 标签的正文转换为干净的纯文本。
    特别处理表格：转换为纯文本表格。
    """
    if not html_content:
        return ""

    # 1. 解码 HTML 实体（如 &nbsp;）
    content = html.unescape(html_content)

    # 2. 使用 BeautifulSoup 解析
    soup = BeautifulSoup(content, "html.parser")

    # 3. 处理表格：将 <table> 转换为可读的文本表格
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            row_cells = []
            for cell in tr.find_all(["th", "td"]):
                # 获取单元格文本，去除多余空格
                cell_text = cell.get_text(strip=True)
                row_cells.append(cell_text)
            if row_cells:
                rows.append(row_cells)

        if rows:
            # 计算每列最大宽度
            col_widths = [max(len(cell) for cell in col) for col in zip(*rows)]
            table_lines = []
            for row in rows:
                # 补齐不足列数
                while len(row) < len(col_widths):
                    row.append("")
                line = "  ".join(cell.ljust(width) for cell, width in zip(row, col_widths))
                table_lines.append(line)
            table_text = "\n".join(table_lines)
            # 用【表格】标记替换原表格
            table.replace_with(f"\n【表格】\n{table_text}\n")

    # 4. 提取纯文本（BeautifulSoup 自动去除标签）
    text = soup.get_text(separator="\n")

    # 5. 清理多余空白行：将连续两个以上换行缩减为两个
    text = re.sub(r'\n\s*\n', '\n\n', text)

    # 6. 去除每行首尾空格，合并行内多余空格
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            # 合并行内连续空格
            line = re.sub(r'\s+', ' ', line)
            lines.append(line)
    cleaned = "\n".join(lines)

    return cleaned