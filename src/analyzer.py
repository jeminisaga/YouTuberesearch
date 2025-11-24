"""
コメントからイベント情報を抽出するモジュール（ルールベース）
"""
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class EventAnalyzer:
    """イベント情報抽出クラス"""
    
    def __init__(self):
        """イベント関連キーワードを初期化"""
        self.event_keywords = [
            '開催', '集合', 'ライブ', 'オフ会', '発売', 'スタート',
            '場所', 'チケット', 'イベント', '会場', '参加', '予約',
            '開始', '終了', '開催日', '日程', '日時'
        ]
        
        # 未来の日付・時間表現のパターン
        self.date_patterns = [
            r'\d{1,2}月\d{1,2}日',  # 1月1日、12月25日
            r'\d{1,2}/\d{1,2}',     # 1/1、12/25
            r'\d{1,2}-\d{1,2}',     # 1-1、12-25
            r'明日',
            r'明後日',
            r'来週',
            r'来月',
            r'今週',
            r'今月',
            r'土曜',
            r'日曜',
            r'月曜',
            r'火曜',
            r'水曜',
            r'木曜',
            r'金曜',
            r'\d{1,2}時',           # 1時、12時
            r'\d{1,2}:\d{2}',       # 12:30
            r'午前\d{1,2}時',
            r'午後\d{1,2}時',
            r'AM\d{1,2}',
            r'PM\d{1,2}',
        ]
        
        # URLパターン（スパム検出用）
        self.url_pattern = re.compile(
            r'https?://[^\s]+|www\.[^\s]+|\.com|\.net|\.org|\.jp'
        )
    
    def contains_future_date(self, text: str) -> bool:
        """
        テキストに未来の日付・時間表現が含まれるかチェック
        
        Args:
            text: チェックするテキスト
        
        Returns:
            未来の日付・時間表現が含まれる場合True
        """
        for pattern in self.date_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def contains_event_keyword(self, text: str) -> bool:
        """
        テキストにイベント関連キーワードが含まれるかチェック
        
        Args:
            text: チェックするテキスト
        
        Returns:
            イベント関連キーワードが含まれる場合True
        """
        text_lower = text.lower()
        for keyword in self.event_keywords:
            if keyword in text_lower:
                return True
        return False
    
    def is_spam(self, text: str) -> bool:
        """
        スパムコメントかどうかを判定
        
        Args:
            text: チェックするテキスト
        
        Returns:
            スパムと判定される場合True
        """
        # URLが含まれる場合はスパムと判定
        if self.url_pattern.search(text):
            return True
        
        # 文字数が極端に短い（5文字未満）または長い（500文字超）場合はスパムと判定
        text_length = len(text.strip())
        if text_length < 5 or text_length > 500:
            return True
        
        return False
    
    def extract_event_info(self, comment: Dict) -> Optional[Dict]:
        """
        コメントからイベント情報を抽出する
        
        Args:
            comment: コメント情報（comment_id, text, author, published_atを含む）
        
        Returns:
            イベント情報が抽出できた場合、辞書を返す。抽出できない場合None。
            返される辞書には以下のキーが含まれる:
            - comment_id: コメントID
            - text: コメント本文
            - author: 著者名
            - published_at: 投稿日時
            - extracted_at: 抽出日時
        """
        text = comment.get('text', '')
        
        # スパムチェック
        if self.is_spam(text):
            return None
        
        # 未来の日付・時間表現が含まれるかチェック
        if not self.contains_future_date(text):
            return None
        
        # イベント関連キーワードが含まれるかチェック
        if not self.contains_event_keyword(text):
            return None
        
        # イベント情報として抽出
        return {
            'comment_id': comment.get('comment_id'),
            'text': text,
            'author': comment.get('author'),
            'published_at': comment.get('published_at'),
            'extracted_at': datetime.utcnow().isoformat() + 'Z'
        }
    
    def analyze_comments(self, comments: List[Dict]) -> List[Dict]:
        """
        コメントリストからイベント情報を抽出する
        
        Args:
            comments: コメント情報のリスト
        
        Returns:
            抽出されたイベント情報のリスト
        """
        events = []
        
        for comment in comments:
            event_info = self.extract_event_info(comment)
            if event_info:
                events.append(event_info)
                logger.debug(f"イベント情報を抽出: {event_info['comment_id']}")
        
        logger.info(f"{len(comments)} 件のコメントから {len(events)} 件のイベント情報を抽出しました")
        return events

