"""
YouTubeコメントからのイベント情報抽出システム
エントリーポイント
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict
from src.fetcher import YouTubeCommentFetcher
from src.analyzer import EventAnalyzer

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_existing_events(data_file: Path) -> List[Dict]:
    """
    既存のイベントデータを読み込む
    
    Args:
        data_file: JSONファイルのパス
    
    Returns:
        既存のイベント情報のリスト
    """
    if not data_file.exists():
        logger.info(f"データファイルが存在しません。新規作成します: {data_file}")
        return []
    
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                logger.warning("データファイルの形式が不正です。空のリストを返します。")
                return []
    except json.JSONDecodeError as e:
        logger.error(f"JSONの解析に失敗しました: {e}")
        return []
    except Exception as e:
        logger.error(f"ファイルの読み込みに失敗しました: {e}")
        return []


def save_events(data_file: Path, events: List[Dict]) -> bool:
    """
    イベントデータをJSONファイルに保存する
    
    Args:
        data_file: JSONファイルのパス
        events: 保存するイベント情報のリスト
    
    Returns:
        保存に成功した場合True
    """
    try:
        # ディレクトリが存在しない場合は作成
        data_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        
        logger.info(f"{len(events)} 件のイベント情報を保存しました: {data_file}")
        return True
    except Exception as e:
        logger.error(f"ファイルの保存に失敗しました: {e}")
        return False


def merge_events(existing_events: List[Dict], new_events: List[Dict]) -> List[Dict]:
    """
    既存のイベントと新規イベントをマージする（重複を除去）
    
    Args:
        existing_events: 既存のイベント情報のリスト
        new_events: 新規のイベント情報のリスト
    
    Returns:
        マージされたイベント情報のリスト
    """
    # comment_idをキーにして既存のイベントを辞書化
    existing_dict = {event['comment_id']: event for event in existing_events}
    
    # 新規イベントを追加（重複は上書き）
    for event in new_events:
        existing_dict[event['comment_id']] = event
    
    # リストに変換して返す
    merged_events = list(existing_dict.values())
    
    # 抽出日時でソート（新しいものから）
    merged_events.sort(key=lambda x: x.get('extracted_at', ''), reverse=True)
    
    return merged_events


def main():
    """メイン処理"""
    # 環境変数から設定を取得
    api_key = os.getenv('YOUTUBE_API_KEY')
    video_id = os.getenv('VIDEO_ID')
    channel_id = os.getenv('CHANNEL_ID')
    category_id = os.getenv('CATEGORY_ID')
    search_keyword = os.getenv('SEARCH_KEYWORD', '副業')  # デフォルト: 副業
    max_videos = int(os.getenv('MAX_VIDEOS', '20'))  # デフォルト: 20件
    max_results = int(os.getenv('MAX_RESULTS', '100'))
    min_comment_count = int(os.getenv('MIN_COMMENT_COUNT', '10'))  # デフォルト: 10件以上
    days_old_max = int(os.getenv('DAYS_OLD_MAX', '7'))  # デフォルト: 7日以内
    
    # APIキーのチェック
    if not api_key:
        logger.error("YOUTUBE_API_KEY が設定されていません")
        return 1
    
    # 動画ID、チャンネルID、カテゴリID、またはキーワードのチェック
    if not video_id and not channel_id and not category_id:
        # キーワードが指定されていない場合、デフォルトで「副業」を使用
        logger.info(f"キーワード検索を使用します: {search_keyword}")
    
    # データファイルのパス
    data_file = Path('data/events.json')
    
    # 既存のイベントデータを読み込む
    existing_events = load_existing_events(data_file)
    logger.info(f"既存のイベント数: {len(existing_events)}")
    
    try:
        # YouTubeコメントを取得
        fetcher = YouTubeCommentFetcher(api_key)
        comments = fetcher.fetch_comments(
            video_id=video_id,
            channel_id=channel_id,
            category_id=category_id,
            search_keyword=search_keyword if not video_id and not channel_id and not category_id else None,
            max_videos=max_videos,
            max_results=max_results,
            min_comment_count=min_comment_count,
            days_old_max=days_old_max
        )
        
        if not comments:
            logger.warning("コメントが取得できませんでした")
            return 0
        
        # イベント情報を抽出
        analyzer = EventAnalyzer()
        new_events = analyzer.analyze_comments(comments)
        
        if not new_events:
            logger.info("新しいイベント情報は見つかりませんでした")
            return 0
        
        # 既存のイベントとマージ
        merged_events = merge_events(existing_events, new_events)
        
        # 変更があったかチェック
        if len(merged_events) == len(existing_events):
            logger.info("新しいイベント情報はありませんでした")
            return 0
        
        # イベントデータを保存
        if save_events(data_file, merged_events):
            logger.info(f"新規イベント {len(merged_events) - len(existing_events)} 件を追加しました")
            return 0
        else:
            logger.error("イベントデータの保存に失敗しました")
            return 1
            
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())

