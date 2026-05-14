"""故事卡加载器"""
import json
import os
from backend.core.config import settings


def load_cards() -> dict:
    """加载所有故事卡定义"""
    path = settings.story_cards_path
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_card(card_id: str) -> dict:
    """获取单张故事卡"""
    cards = load_cards()
    return cards.get(card_id)


def list_cards() -> list:
    """列出所有故事卡"""
    cards = load_cards()
    result = []
    for cid, card in cards.items():
        result.append({
            "id": cid,
            "name": card.get("name", ""),
            "category": card.get("category", ""),
            "description": card.get("description", ""),
            "difficulty": card.get("difficulty", "intermediate"),
            "reference_works": card.get("reference_works", []),
        })
    return result
