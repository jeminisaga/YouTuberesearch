"""
YouTube Data API v3を使用してコメントを取得するモジュール
"""
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)


class YouTubeCommentFetcher:
    """YouTubeコメント取得クラス"""
    
    def __init__(self, api_key: str):
        """
        Args:
            api_key: YouTube Data API v3のAPIキー
        """
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
    
    def get_video_comments(self, video_id: str, max_results: int = 100) -> List[Dict]:
        """
        指定された動画のコメントを取得する
        
        Args:
            video_id: YouTube動画ID
            max_results: 取得する最大コメント数（デフォルト: 100）
        
        Returns:
            コメント情報のリスト。各要素は以下のキーを持つ:
            - comment_id: コメントID
            - text: コメント本文
            - author: 著者名
            - published_at: 投稿日時（ISO形式）
        """
        comments = []
        
        try:
            # コメントスレッドを取得
            request = self.youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=min(max_results, 100),  # APIの最大値は100
                order='time',  # 最新順
                textFormat='plainText'
            )
            
            response = request.execute()
            
            while len(comments) < max_results and 'items' in response:
                for item in response['items']:
                    if len(comments) >= max_results:
                        break
                    
                    snippet = item['snippet']['topLevelComment']['snippet']
                    comments.append({
                        'comment_id': item['snippet']['topLevelComment']['id'],
                        'text': snippet['textDisplay'],
                        'author': snippet['authorDisplayName'],
                        'published_at': snippet['publishedAt']
                    })
                
                # 次のページがある場合
                if 'nextPageToken' in response and len(comments) < max_results:
                    request = self.youtube.commentThreads().list(
                        part='snippet',
                        videoId=video_id,
                        maxResults=min(max_results - len(comments), 100),
                        pageToken=response['nextPageToken'],
                        order='time',
                        textFormat='plainText'
                    )
                    response = request.execute()
                else:
                    break
            
            logger.info(f"動画 {video_id} から {len(comments)} 件のコメントを取得しました")
            return comments
            
        except HttpError as e:
            error_content = e.content.decode('utf-8') if e.content else str(e)
            if e.resp.status == 403:
                logger.error(f"APIキーが無効またはクォータが不足しています: {error_content}")
            elif e.resp.status == 404:
                logger.error(f"動画が見つかりません: {video_id}")
            else:
                logger.error(f"APIエラーが発生しました: {error_content}")
            return []
        except Exception as e:
            logger.error(f"予期しないエラーが発生しました: {str(e)}")
            return []
    
    def get_channel_latest_videos(self, channel_id: str, max_results: int = 5) -> List[str]:
        """
        チャンネルの最新動画IDリストを取得する
        
        Args:
            channel_id: YouTubeチャンネルID
            max_results: 取得する最大動画数（デフォルト: 5）
        
        Returns:
            動画IDのリスト
        """
        video_ids = []
        
        try:
            # チャンネルのアップロードプレイリストIDを取得
            channel_response = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            ).execute()
            
            if not channel_response.get('items'):
                logger.error(f"チャンネルが見つかりません: {channel_id}")
                return []
            
            uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # プレイリストから動画を取得
            request = self.youtube.playlistItems().list(
                part='contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=max_results
            )
            
            response = request.execute()
            
            for item in response.get('items', []):
                video_ids.append(item['contentDetails']['videoId'])
            
            logger.info(f"チャンネル {channel_id} から {len(video_ids)} 件の動画を取得しました")
            return video_ids
            
        except HttpError as e:
            error_content = e.content.decode('utf-8') if e.content else str(e)
            if e.resp.status == 403:
                logger.error(f"APIキーが無効またはクォータが不足しています: {error_content}")
            elif e.resp.status == 404:
                logger.error(f"チャンネルが見つかりません: {channel_id}")
            else:
                logger.error(f"APIエラーが発生しました: {error_content}")
            return []
        except Exception as e:
            logger.error(f"予期しないエラーが発生しました: {str(e)}")
            return []
    
    def get_video_statistics(self, video_ids: List[str]) -> Dict[str, Dict]:
        """
        動画の統計情報（コメント数、投稿日時など）を取得する
        
        Args:
            video_ids: 動画IDのリスト
        
        Returns:
            動画IDをキーとした統計情報の辞書
        """
        if not video_ids:
            return {}
        
        statistics = {}
        
        try:
            # 50件ずつ処理（APIの最大値）
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i+50]
                
                request = self.youtube.videos().list(
                    part='statistics,snippet',
                    id=','.join(batch_ids)
                )
                
                response = request.execute()
                
                for item in response.get('items', []):
                    video_id = item['id']
                    stats = item.get('statistics', {})
                    snippet = item.get('snippet', {})
                    
                    statistics[video_id] = {
                        'comment_count': int(stats.get('commentCount', 0)),
                        'view_count': int(stats.get('viewCount', 0)),
                        'published_at': snippet.get('publishedAt', ''),
                        'title': snippet.get('title', '')
                    }
            
            return statistics
            
        except HttpError as e:
            error_content = e.content.decode('utf-8') if e.content else str(e)
            logger.error(f"動画統計情報の取得に失敗しました: {error_content}")
            return {}
        except Exception as e:
            logger.error(f"予期しないエラーが発生しました: {str(e)}")
            return {}
    
    def search_videos_by_keyword(self, keyword: str, max_videos: int = 10, order: str = 'date',
                                 min_comment_count: int = 10, days_old_max: int = 7) -> List[str]:
        """
        キーワードで動画を検索し、コメント数と投稿日時でフィルタリングする
        
        Args:
            keyword: 検索キーワード（例: '副業', '在宅ワーク'）
            max_videos: 取得する最大動画数（デフォルト: 10）
            order: ソート順（'date': 最新順）
            min_comment_count: 最小コメント数（デフォルト: 10）
            days_old_max: 最大投稿日数（デフォルト: 7日以内）
        
        Returns:
            フィルタリングされた動画IDのリスト
        """
        candidate_video_ids = []
        
        try:
            # まず多めに検索（フィルタリングで減ることを考慮）
            search_limit = max_videos * 3  # 3倍検索してフィルタリング
            
            request = self.youtube.search().list(
                part='id',
                type='video',
                q=keyword,
                maxResults=min(search_limit, 50),  # APIの最大値は50
                order=order
            )
            
            response = request.execute()
            
            while len(candidate_video_ids) < search_limit and 'items' in response:
                for item in response['items']:
                    if len(candidate_video_ids) >= search_limit:
                        break
                    if item['id']['kind'] == 'youtube#video':
                        candidate_video_ids.append(item['id']['videoId'])
                
                # 次のページがある場合
                if 'nextPageToken' in response and len(candidate_video_ids) < search_limit:
                    request = self.youtube.search().list(
                        part='id',
                        type='video',
                        q=keyword,
                        maxResults=min(search_limit - len(candidate_video_ids), 50),
                        pageToken=response['nextPageToken'],
                        order=order
                    )
                    response = request.execute()
                else:
                    break
            
            if not candidate_video_ids:
                logger.warning(f"キーワード '{keyword}' から動画が見つかりませんでした")
                return []
            
            # 統計情報を取得
            statistics = self.get_video_statistics(candidate_video_ids)
            
            # フィルタリングとソート
            filtered_videos = []
            now = datetime.utcnow()
            
            for video_id in candidate_video_ids:
                if video_id not in statistics:
                    continue
                
                stats = statistics[video_id]
                comment_count = stats['comment_count']
                published_at_str = stats['published_at']
                
                # コメント数チェック
                if comment_count < min_comment_count:
                    continue
                
                # 投稿日時チェック
                try:
                    published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                    days_old = (now - published_at.replace(tzinfo=None)).days
                    
                    if days_old > days_old_max:
                        continue
                except Exception:
                    # 日付解析に失敗した場合はスキップ
                    continue
                
                filtered_videos.append({
                    'video_id': video_id,
                    'comment_count': comment_count,
                    'days_old': days_old,
                    'published_at': published_at_str
                })
            
            # コメント数が多い順、最新順でソート
            filtered_videos.sort(key=lambda x: (-x['comment_count'], x['days_old']))
            
            # 最大件数まで取得
            result_video_ids = [v['video_id'] for v in filtered_videos[:max_videos]]
            
            logger.info(f"キーワード '{keyword}' から {len(result_video_ids)} 件の動画を検索しました（候補: {len(candidate_video_ids)}件、フィルタ後: {len(filtered_videos)}件）")
            return result_video_ids
            
        except HttpError as e:
            error_content = e.content.decode('utf-8') if e.content else str(e)
            if e.resp.status == 403:
                logger.error(f"APIキーが無効またはクォータが不足しています: {error_content}")
            else:
                logger.error(f"APIエラーが発生しました: {error_content}")
            return []
        except Exception as e:
            logger.error(f"予期しないエラーが発生しました: {str(e)}")
            return []
    
    def search_videos_by_category(self, category_id: str, max_videos: int = 10, order: str = 'date') -> List[str]:
        """
        カテゴリIDで動画を検索する
        
        Args:
            category_id: YouTubeカテゴリID（例: '10'=Music, '20'=Gaming）
            max_videos: 取得する最大動画数（デフォルト: 10）
            order: ソート順（'date': 最新順, 'rating': 評価順, 'viewCount': 再生数順）
        
        Returns:
            動画IDのリスト
        """
        video_ids = []
        
        try:
            request = self.youtube.search().list(
                part='id',
                type='video',
                videoCategoryId=category_id,
                maxResults=min(max_videos, 50),  # APIの最大値は50
                order=order,
                publishedAfter=None  # 必要に応じて日付フィルタを追加可能
            )
            
            response = request.execute()
            
            while len(video_ids) < max_videos and 'items' in response:
                for item in response['items']:
                    if len(video_ids) >= max_videos:
                        break
                    if item['id']['kind'] == 'youtube#video':
                        video_ids.append(item['id']['videoId'])
                
                # 次のページがある場合
                if 'nextPageToken' in response and len(video_ids) < max_videos:
                    request = self.youtube.search().list(
                        part='id',
                        type='video',
                        videoCategoryId=category_id,
                        maxResults=min(max_videos - len(video_ids), 50),
                        pageToken=response['nextPageToken'],
                        order=order
                    )
                    response = request.execute()
                else:
                    break
            
            logger.info(f"カテゴリ {category_id} から {len(video_ids)} 件の動画を検索しました")
            return video_ids
            
        except HttpError as e:
            error_content = e.content.decode('utf-8') if e.content else str(e)
            if e.resp.status == 403:
                logger.error(f"APIキーが無効またはクォータが不足しています: {error_content}")
            else:
                logger.error(f"APIエラーが発生しました: {error_content}")
            return []
        except Exception as e:
            logger.error(f"予期しないエラーが発生しました: {str(e)}")
            return []
    
    def fetch_comments(self, video_id: Optional[str] = None, channel_id: Optional[str] = None, 
                      category_id: Optional[str] = None, search_keyword: Optional[str] = None,
                      max_videos: int = 20, max_results: int = 100,
                      min_comment_count: int = 10, days_old_max: int = 7) -> List[Dict]:
        """
        動画ID、チャンネルID、カテゴリID、またはキーワードからコメントを取得する
        
        Args:
            video_id: 動画ID（指定された場合、この動画のコメントを取得）
            channel_id: チャンネルID（指定された場合、最新動画のコメントを取得）
            category_id: カテゴリID（指定された場合、そのカテゴリの最新動画のコメントを取得）
            search_keyword: 検索キーワード（指定された場合、そのキーワードで動画を検索）
            max_videos: 検索する最大動画数（category_idまたはsearch_keyword使用時、デフォルト: 20）
            max_results: 取得する最大コメント数
            min_comment_count: 最小コメント数（デフォルト: 10）
            days_old_max: 最大投稿日数（デフォルト: 7日以内）
        
        Returns:
            コメント情報のリスト
        """
        if video_id:
            return self.get_video_comments(video_id, max_results)
        elif channel_id:
            video_ids = self.get_channel_latest_videos(channel_id, max_results=5)
            all_comments = []
            for vid in video_ids:
                comments = self.get_video_comments(vid, max_results // len(video_ids) + 1)
                all_comments.extend(comments)
                if len(all_comments) >= max_results:
                    break
            return all_comments[:max_results]
        elif search_keyword:
            # キーワードで動画を検索（フィルタリング付き）
            video_ids = self.search_videos_by_keyword(
                search_keyword, 
                max_videos=max_videos, 
                order='date',
                min_comment_count=min_comment_count,
                days_old_max=days_old_max
            )
            if not video_ids:
                logger.warning(f"キーワード '{search_keyword}' から動画が見つかりませんでした")
                return []
            
            all_comments = []
            comments_per_video = max_results // len(video_ids) + 1
            for vid in video_ids:
                comments = self.get_video_comments(vid, comments_per_video)
                all_comments.extend(comments)
                if len(all_comments) >= max_results:
                    break
            return all_comments[:max_results]
        elif category_id:
            # カテゴリから動画を検索（簡易版、フィルタリングなし）
            video_ids = self.search_videos_by_category(category_id, max_videos=max_videos, order='date')
            if not video_ids:
                logger.warning(f"カテゴリ {category_id} から動画が見つかりませんでした")
                return []
            
            all_comments = []
            comments_per_video = max_results // len(video_ids) + 1
            for vid in video_ids:
                comments = self.get_video_comments(vid, comments_per_video)
                all_comments.extend(comments)
                if len(all_comments) >= max_results:
                    break
            return all_comments[:max_results]
        else:
            logger.error("video_id、channel_id、category_id、またはsearch_keywordのいずれかを指定してください")
            return []

