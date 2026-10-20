"""集中放配置：路径、日期、模型名。其它文件都从这里读。"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DB_PATH = Path(os.getenv("BANK_DB", ROOT / "data" / "bank.db"))
POLICY_DIR = ROOT / "docs" / "policies"
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ROOT / ".chroma"))

# 为了让结果可重复，"今天"固定为这个日期（数据也是围绕这个日期生成的）
AS_OF_DATE = "2026-10-01"

LLM_MODEL = os.getenv("LLM_MODEL", "deepseek:deepseek-chat")
# EMBEDDINGS=fake 时用不需要下载模型的假向量，只给测试用
EMBEDDINGS = os.getenv("EMBEDDINGS", "default")
