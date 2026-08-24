# Ryuute

「予定」だけでなく、**その予定に間に合うために必要な移動時間まで管理する**Webスケジュール帳です。

通常の予定・タスク管理に加えて、予定の場所から経路を検索し、移動時間を予定の直前に組み込んで表示します。

例えば10:30開始の予定へ向かうのに1時間必要なら、カレンダー上では次のように扱います。

```text
09:20 - 10:20  移動
10:30 - 12:00  予定
```

「10:30に予定がある」だけではなく、**「09:20には移動を始める必要がある」**ところまで分かることがRyuuteの中心機能です。

---

# 1. 2026-08-24時点の方針

このREADMEを今後の実装仕様の基準とします。

現在のリポジトリにはReact / FastAPI / SQLiteによる予定・タスク管理、予定詳細、経路検索UI、TravelPlan API、準備チェックリスト・準備案内などが実装されています。

一方、バックエンドの経路検索サービスにはGoogle Routes APIを利用した既存実装が残っています。日本の公共交通経路取得で期待した結果を安定して得られなかったため、**経路検索の本番APIを駅すぱあと API スタンダードへ変更**します。

また、場所入力にはGoogle Places Autocompleteを利用し、予定詳細からGoogle Mapsを開けるようにします。

最終デモでは外部の経路API接続に依存してデモ全体が失敗しないよう、**駅すぱあとのレスポンス構造を模したMock JSON**をバックエンドで読み込み、本番時と同じアプリ用JSONへ変換して返します。

```text
場所入力          Google Places Autocomplete
地図リンク        Google Maps URLs
公共交通経路検索  駅すぱあと API スタンダード
デモ経路          駅すぱあと形式のMock JSON
```

Google Routes APIは新仕様では経路検索に使用しません。

---

# 2. 技術構成

| 項目 | 技術 |
| --- | --- |
| フロントエンド | React |
| ビルドツール | Vite |
| バックエンド | FastAPI |
| データベース | SQLite |
| 場所候補・場所情報 | Google Places Autocomplete |
| 地図リンク | Google Maps URLs |
| 公共交通経路検索 | 駅すぱあと API スタンダード |
| HTTPクライアント | httpx |
| 通信形式 | JSON |

全体構成は次のとおりです。

```text
React
  |
  | HTTP / JSON
  v
FastAPI
  |
  +------ SQLite
  |
  +------ Route Provider
             |
             +------ Mock Provider      <- デモ
             |
             +------ Ekispert Provider  <- 本番

React
  |
  +------ Google Places Autocomplete
  |
  +------ Google Maps URL
```

フロントエンドは駅すぱあとの生レスポンスを扱いません。

駅すぱあと固有のデータ構造はFastAPI側でアプリ共通形式へ変換します。

---

# 3. アプリの主要機能

## 3.1 カレンダー

以下の表示を用意します。

- 月表示
- 週表示
- タスク表示

### 月表示

1か月分の予定を表示します。

日付セルをクリックすると、その日を初期値とした予定追加モーダルを開きます。

### 週表示

1週間分の予定を時間軸上に表示します。

通常予定に加えて、登録済みの移動予定も時間ブロックとして表示します。

```text
09:00

09:20 ┌────────────────┐
      │ 移動            │
      │ -> Garraway F   │
10:20 └────────────────┘

10:30 ┌────────────────┐
      │ ハッカソン      │
      │ Garraway F      │
12:00 └────────────────┘
```

空いている時間帯をクリックすると、その日時を初期値とした予定追加モーダルを開きます。

### タスク表示

タスクを一覧表示し、未完了と完了済みを分けて扱います。

---

# 4. 予定機能

## 4.1 予定追加

予定追加モーダルは以下から開きます。

- ヘッダーの「追加」
- 月カレンダーの日付
- 週カレンダーの空き時間

予定には以下の情報を持たせます。

| 項目 | 必須 | 説明 |
| --- | --- | --- |
| `title` | 必須 | 予定タイトル |
| `start_at` | 必須 | 開始日時 |
| `end_at` | 必須 | 終了日時 |
| `description` | 任意 | 説明 |
| `location_name` | 任意 | ユーザーへ表示する場所名 |
| `destination` | 任意 | 住所。経路検索のフォールバックにも使用 |
| `destination_place_id` | 任意 | Google Place ID |
| `destination_lat` | 任意 | 緯度 |
| `destination_lng` | 任意 | 経度 |
| `arrival_buffer_minutes` | 任意 | 予定開始何分前までに到着したいか |

日時はアプリ内では `YYYY-MM-DDTHH:mm` のローカル日時として扱います。

`arrival_buffer_minutes` が未設定の場合は、経路検索時に0分として扱います。

---

# 5. 場所入力とGoogle Places Autocomplete

## 5.1 基本仕様

場所入力にはGoogle Places Autocompleteを使用します。

Autocompleteは以下で共通利用します。

- 予定追加時の場所入力
- 予定編集時の場所入力
- 経路検索時の出発地入力

入力中は候補を表示し、ユーザーが候補を選択した場合は最低限次の情報を取得します。

```text
name
address
place_id
lat
lng
```

予定では次のように保存します。

```text
name      -> events.location_name
address   -> events.destination
place_id  -> events.destination_place_id
lat       -> events.destination_lat
lng       -> events.destination_lng
```

## 5.2 手入力の扱い

Autocomplete候補を選択しなくても通常予定として保存できるようにします。

候補を選択していない場合は、入力文字列を `location_name` または `destination` として保存できます。

ただし、経路検索では座標がある方が安定するため、経路検索を利用する予定についてはAutocomplete候補の選択を推奨します。

経路検索時は次の優先順位で地点を決定します。

```text
1. 緯度・経度
2. 住所文字列
```

---

# 6. Google Mapsリンク

予定詳細では、場所が設定されている場合にGoogle Mapsを開けるようにします。

URL自体はDBへ保存せず、表示時に生成します。

Place IDがある場合は、Google Maps Search URLの `query_place_id` を使用して対象施設をできるだけ一意に開きます。

Place IDがない場合は、場所名または住所だけを `query` に使用します。

Google Maps URLを開くためのAPIキーは不要です。

---

# 7. 予定詳細

予定をクリックすると予定詳細モーダルを表示します。

予定詳細では以下を行います。

- 予定内容の確認
- 場所からGoogle Mapsを開く
- 予定の編集
- 予定の削除
- 準備チェックリストの確認・追加・編集・削除
- 準備項目の完了状態の切り替え
- 登録済み移動予定の確認
- 経路検索
- 経路再検索

場所に経路検索可能な情報がない予定では、経路検索ボタンを表示しない、またはdisabledにします。

---

# 8. 経路検索

## 8.1 入口

主なフローは次のとおりです。

```text
カレンダー
   ↓
予定をクリック
   ↓
予定詳細
   ↓
「経路を検索」
   ↓
経路検索モーダル
```

## 8.2 出発地

出発地はユーザー設定として保存しません。

経路検索のたびに入力し、Google Places Autocompleteから選択できます。

出発地をDBやlocalStorageへ保存する設定機能は設けません。

## 8.3 到着希望日時

到着希望日時はバックエンドで計算します。

```text
desired_arrival_at
= event.start_at - event.arrival_buffer_minutes
```

`arrival_buffer_minutes` が `null` の場合は0分です。

---

# 9. Route Search API

## 9.1 Endpoint

```http
POST /api/events/{event_id}/route-search
```

## 9.2 Request

```json
{
  "origin_name": "九州大学 伊都キャンパス",
  "origin_address": "福岡県福岡市西区元岡744",
  "origin_place_id": "GOOGLE_PLACE_ID",
  "origin_lat": 33.596,
  "origin_lng": 130.215
}
```

`origin_place_id` は駅すぱあとへ直接送信しません。

経路探索には主に `origin_lat` / `origin_lng` を使用します。

座標がない場合は `origin_address`、それもなければ `origin_name` をフォールバックとして利用します。

目的地はEventから取得します。

## 9.3 バックエンド処理

```text
POST /api/events/{event_id}/route-search
        ↓
Event取得
        ↓
目的地取得
        ↓
予定開始 - 到着余裕時間
        ↓
desired_arrival_at
        ↓
Route Provider
        ↓
駅すぱあと形式レスポンス
        ↓
convert_ekispert_route()
        ↓
アプリ共通Route JSON
        ↓
React
```

検索しただけではTravelPlanを保存しません。

---

# 10. 駅すぱあと API スタンダード

公共交通の検索には `GET /v1/json/search/course/extreme` を使用します。

主なパラメータ：

```text
key=<EKISPERT_API_KEY>
viaList=<出発地点>:<目的地点>
gcs=wgs84
date=YYYYMMDD
time=HHMM
searchType=arrival
answerCount=1
sort=ekispert
```

MVPでは1件の経路だけを表示するため `answerCount=1` とします。

予定へ間に合う経路を検索するため `searchType=arrival` を使用します。

Google Placesから取得した緯度経度はWGS84として扱い、駅すぱあと側でも `gcs=wgs84` を指定します。

## 10.1 徒歩区間について

駅すぱあとへ座標を指定した場合、座標から最寄り駅までの移動時間は実際の道路経路ではなく概算です。

MVPでは次の仕様とします。

```text
鉄道・公共交通のダイヤ  -> 駅すぱあと
施設 <-> 最寄り駅の徒歩 -> 駅すぱあとによる概算
```

---

# 11. Route Provider

外部API固有処理をフロントエンドやFastAPIのEndpointへ直接埋め込まないため、経路取得処理をProviderとして分離します。

```text
backend/
├── main.py
├── database.py
├── routes_service.py
├── route_providers/
│   ├── mock_provider.py
│   └── ekispert_provider.py
└── fixtures/
    └── ekispert_route_demo.json
```

実際のファイル分割は変更して構いませんが、責務は分離します。

```text
Mock Provider
    ↓
駅すぱあと形式Mock JSON
    ↓
convert_ekispert_route()
    ↓
アプリ共通JSON
```

```text
Ekispert Provider
    ↓
駅すぱあと API
    ↓
駅すぱあと生JSON
    ↓
convert_ekispert_route()
    ↓
アプリ共通JSON
```

**Mockでも本番でも、変換処理より後ろは同じコードを使います。**

---

# 12. デモ用Mock JSON

デモ用Mockは、アプリ共通JSONを直接返すのではなく、**駅すぱあとの生レスポンスのうちアプリで利用する構造を模したfixture**とします。

想定ファイル：

```text
backend/fixtures/ekispert_route_demo.json
```

デモケース：

```text
出発地: 九州大学 伊都キャンパス
目的地: Garraway F
```

駅すぱあとのJSONでは、要素数によって同じキーが単一オブジェクトまたは配列になる場合があるため、変換処理側で正規化して扱います。

```python
def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
```

---

# 13. アプリ共通Route JSON

```json
{
  "origin": "九州大学 伊都キャンパス",
  "destination": "Garraway F",
  "departure_at": "2026-08-25T08:59",
  "arrival_at": "2026-08-25T10:12",
  "duration_minutes": 73,
  "transport_mode": "TRANSIT",
  "segments": [
    {
      "type": "WALK",
      "from": "九州大学 伊都キャンパス",
      "to": "九大学研都市",
      "departure_at": "2026-08-25T08:59",
      "arrival_at": "2026-08-25T09:14",
      "duration_minutes": 15,
      "line_name": null
    },
    {
      "type": "TRANSIT",
      "from": "九大学研都市",
      "to": "天神",
      "departure_at": "2026-08-25T09:20",
      "arrival_at": "2026-08-25T10:02",
      "duration_minutes": 42,
      "line_name": "JR筑肥線・福岡市地下鉄空港線"
    },
    {
      "type": "WALK",
      "from": "天神",
      "to": "Garraway F",
      "departure_at": "2026-08-25T10:02",
      "arrival_at": "2026-08-25T10:12",
      "duration_minutes": 10,
      "line_name": null
    }
  ]
}
```

フロントエンド、TravelPlan API、DBでは駅すぱあとの生レスポンスを扱いません。

---

# 14. 経路検索結果UI

MVPでは1つの経路を縦型で表示します。

```text
08:59                  10:12
出発          73分       到着

九州大学 伊都キャンパス
│
│ 徒歩 15分
│
九大学研都市
│
│ JR筑肥線・福岡市地下鉄空港線
│ 09:20 -> 10:02
│
天神
│
│ 徒歩 10分
│
Garraway F

[ この経路を登録 ]
```

検索しただけではTravelPlanを保存しません。

ユーザーが「この経路を登録」を押した時点で保存します。

---

# 15. 移動予定 TravelPlan

移動予定は通常予定とは別の `travel_plans` テーブルへ保存します。

1つの予定につき1件とします。

同じ予定に新しい経路を登録した場合は上書きします。

予定を削除した場合はTravelPlanも削除します。

---

# 16. DB共通仕様

SQLiteを使用します。

日時はMVPでは次の文字列形式で保存します。

```text
YYYY-MM-DDTHH:mm
```

使用するテーブルは次の4つです。

```text
events
tasks
travel_plans
event_preparations
```

出発地点を保存する `settings` テーブルは使用しません。

---

# 17. eventsテーブル

| カラム | SQLite型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `id` | INTEGER | 必須 | 主キー、AUTOINCREMENT |
| `title` | TEXT | 必須 | 予定タイトル |
| `start_at` | TEXT | 必須 | 開始日時 |
| `end_at` | TEXT | 必須 | 終了日時 |
| `description` | TEXT | 必須 | 未入力時は空文字 |
| `location_name` | TEXT | 任意 | 表示用の場所名 |
| `destination` | TEXT | 任意 | 住所・目的地文字列 |
| `destination_place_id` | TEXT | 任意 | Google Place ID |
| `destination_lat` | REAL | 任意 | WGS84緯度 |
| `destination_lng` | REAL | 任意 | WGS84経度 |
| `arrival_buffer_minutes` | INTEGER | 任意 | 予定開始何分前までに到着するか |

---

# 18. tasksテーブル

| カラム | SQLite型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `id` | INTEGER | 必須 | 主キー、AUTOINCREMENT |
| `title` | TEXT | 必須 | タスクタイトル |
| `due_at` | TEXT | 任意 | 期限 |
| `description` | TEXT | 必須 | 未入力時は空文字 |
| `completed` | INTEGER | 必須 | 未完了0、完了1 |

---

# 19. travel_plansテーブル

| カラム | SQLite型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `id` | INTEGER | 必須 | 主キー、AUTOINCREMENT |
| `event_id` | INTEGER | 必須 | 対応する予定、UNIQUE |
| `origin` | TEXT | 必須 | 検索時の出発地表示名 |
| `destination` | TEXT | 必須 | 検索時の目的地表示名 |
| `departure_at` | TEXT | 必須 | 出発日時 |
| `arrival_at` | TEXT | 必須 | 到着日時 |
| `duration_minutes` | INTEGER | 必須 | 所要時間 |
| `transport_mode` | TEXT | 必須 | 主な移動手段 |
| `route_details` | TEXT | 必須 | segmentsをJSON文字列として保存 |

駅すぱあとの生レスポンスはDBへ保存しません。

---

# 20. event_preparationsテーブル

予定ごとに持ち物・事前準備を登録します。

| カラム | SQLite型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `id` | INTEGER | 必須 | 主キー、AUTOINCREMENT |
| `event_id` | INTEGER | 必須 | 対応する予定 |
| `title` | TEXT | 必須 | 準備項目名 |
| `completed` | INTEGER | 必須 | 未完了0、完了1 |

予定削除時は `ON DELETE CASCADE` で準備項目も削除します。

---

# 21. 準備チェックリスト・準備案内

予定詳細モーダルに準備チェックリストを表示します。

準備項目は以下を操作できます。

- 追加
- 編集
- 削除
- 完了 / 未完了切り替え

通知期間は全予定共通で以下から選択します。

```text
1時間前
3時間前
1日前
3日前
7日前
```

初期値は3日前です。

設定は `localStorage` に保存します。

ブラウザNotifications API、Service Worker、外部通知サービスは使用しません。

---

# 22. API一覧

## Health

```http
GET /api/health
```

## Event

```http
GET    /api/events
POST   /api/events
PUT    /api/events/{event_id}
DELETE /api/events/{event_id}
```

## Route Search

```http
POST /api/events/{event_id}/route-search
```

## TravelPlan

```http
GET    /api/events/{event_id}/travel-plan
PUT    /api/events/{event_id}/travel-plan
DELETE /api/events/{event_id}/travel-plan
```

## Preparation

```http
GET    /api/preparations
GET    /api/events/{event_id}/preparations
POST   /api/events/{event_id}/preparations
PUT    /api/events/{event_id}/preparations/{preparation_id}
DELETE /api/events/{event_id}/preparations/{preparation_id}
```

## Task

```http
GET    /api/tasks
POST   /api/tasks
PUT    /api/tasks/{task_id}
DELETE /api/tasks/{task_id}
```

---

# 23. 環境変数

APIキーをGitへpushしません。

## バックエンド

```text
EKISPERT_API_KEY=
ROUTE_PROVIDER=mock
```

`ROUTE_PROVIDER`:

```text
mock       デモ用fixtureを使用
ekispert   駅すぱあとAPIを使用
```

最終デモでは原則 `mock` を使用します。

## フロントエンド

```text
VITE_GOOGLE_MAPS_API_KEY=
```

ブラウザ用Google Maps PlatformキーはGoogle Cloud側でHTTPリファラと利用APIを制限します。

---

# 24. 起動方法

## バックエンド

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload
```

## フロントエンド

```bash
cd frontend
npm install
npm run dev
```

---

# 25. デモで見せる中心フロー

```text
1. 予定を追加
   ↓
2. Google Places Autocompleteで場所を選択
   ↓
3. 予定詳細を開く
   ↓
4. Google Mapsを開けることを見せる
   ↓
5. 「経路を検索」
   ↓
6. 出発地をAutocompleteで選択
   ↓
7. FastAPIへRoute Search Request
   ↓
8. Mock Providerが駅すぱあと形式fixtureを読む
   ↓
9. convert_ekispert_route()でアプリ共通JSONへ変換
   ↓
10. 縦型の経路結果を表示
   ↓
11. 「この経路を登録」
   ↓
12. TravelPlanをSQLiteへ保存
   ↓
13. 週カレンダーに移動予定を表示
```

可能であれば準備チェックリスト・準備案内も紹介します。

---

# 26. 本番APIとMockの考え方

```text
デモ
fixture -> converter -> FastAPI -> React -> SQLite

本番
Ekispert -> converter -> FastAPI -> React -> SQLite
```

違うのは最初のデータ取得部分だけです。

---

# 27. 実装上の優先順位

```text
最優先
1. Google Places Autocomplete
2. Google Mapsリンク
3. EventへPlace ID / 座標を保存
4. 駅すぱあと形式Mock fixture
5. convert_ekispert_route()
6. Route Provider切り替え
7. Mockで検索 -> 表示 -> TravelPlan登録まで通す
8. 週カレンダーへ移動予定を表示

余裕があれば
9. 駅すぱあとスタンダードへ実接続
10. 実APIレスポンスでfixtureとの差異を修正
```

外部API実接続のために、Mockで完成しているデモフローを壊さないことを優先します。
