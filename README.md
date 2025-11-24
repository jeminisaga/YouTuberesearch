# YouTubeコメントからのイベント情報抽出システム

YouTubeの指定した動画、チャンネル、またはジャンル（カテゴリ）のコメント欄から、イベント開催情報を自動抽出してJSONファイルに蓄積するシステムです。

## 機能

- YouTube Data API v3を使用したコメント取得
- ルールベースによるイベント情報の自動抽出
- GitHub Actionsによる定期自動実行（毎日9:00 JST）
- 増分更新による重複排除

## セットアップ

### 1. GitHub Secretsの設定

リポジトリの「Settings」→「Secrets and variables」→「Actions」で以下を設定：

#### 必須
- `YOUTUBE_API_KEY`: YouTube Data API v3のAPIキー

#### いずれか1つを設定（優先順位: VIDEO_ID > CHANNEL_ID > CATEGORY_ID > SEARCH_KEYWORD）
- `VIDEO_ID`: 特定の動画ID（例: `dQw4w9WgXcQ`）
- `CHANNEL_ID`: チャンネルID（例: `UCxxxxxxxxxxxxxxxxxxxxxx`）
- `CATEGORY_ID`: カテゴリID（ジャンル指定、下記参照）
- `SEARCH_KEYWORD`: 検索キーワード（例: `副業`, `在宅ワーク`。デフォルト: `副業`）

#### オプション
- `MAX_VIDEOS`: 検索する最大動画数（デフォルト: `20`）
- `MAX_RESULTS`: 取得する最大コメント数（デフォルト: `100`）

### 2. YouTubeカテゴリID一覧

カテゴリIDを指定すると、そのジャンルの最新動画のコメントを取得します。

| カテゴリID | ジャンル名 |
|-----------|-----------|
| 1 | Film & Animation（映画・アニメ） |
| 2 | Autos & Vehicles（自動車・乗り物） |
| 10 | Music（音楽） |
| 15 | Pets & Animals（ペット・動物） |
| 17 | Sports（スポーツ） |
| 19 | Travel & Events（旅行・イベント） |
| 20 | Gaming（ゲーム） |
| 22 | People & Blogs（人物・ブログ） |
| 23 | Comedy（コメディ） |
| 24 | Entertainment（エンターテイメント） |
| 25 | News & Politics（ニュース・政治） |
| 26 | Howto & Style（ハウツー・スタイル） |
| 27 | Education（教育） |
| 28 | Science & Technology（科学・技術） |

### 3. ローカルでの実行

```bash
# 依存ライブラリのインストール
pip install -r requirements.txt

# 環境変数の設定
export YOUTUBE_API_KEY="your_api_key"
export SEARCH_KEYWORD="副業"  # キーワード検索（デフォルト: 副業）
export MAX_VIDEOS="20"  # 検索する動画数（デフォルト: 20）

# 実行
python main.py
```

## データ形式

`data/events.json`に以下の形式でイベント情報が保存されます：

```json
[
  {
    "comment_id": "コメントID",
    "text": "コメント本文",
    "author": "著者名",
    "published_at": "投稿日時（ISO形式）",
    "extracted_at": "抽出日時（ISO形式）"
  }
]
```

## イベント抽出ロジック

以下の条件をすべて満たすコメントがイベント情報として抽出されます：

1. **未来の日付・時間表現が含まれる**
   - 例: `1月1日`, `12/25`, `明日`, `来週`, `土曜`, `12時` など

2. **イベント関連キーワードが含まれる**
   - キーワード: `開催`, `集合`, `ライブ`, `オフ会`, `発売`, `スタート`, `場所`, `チケット` など

3. **スパム除外**
   - URLが含まれるもの
   - 文字数が5文字未満または500文字超のもの

## 自動実行

GitHub Actionsにより毎日日本時間9:00（UTC 0:00）に自動実行されます。
新しいイベント情報が見つかった場合のみ、`data/events.json`が自動更新され、コミットされます。

## ライセンス

MIT License

