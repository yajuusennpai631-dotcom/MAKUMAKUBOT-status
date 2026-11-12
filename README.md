# MAKUMAKUBOT Status

公開用のRailwayステータスページです。ワークスペース内のプロジェクト・サービスを読み取り専用で取得し、60秒間隔で表示を更新します。

## Deploy

Railwayでこのリポジトリを新しいサービスとしてデプロイしてください。Python / FastAPI を自動検出します。起動コマンドは次のとおりです。

```sh
uvicorn app:app --host 0.0.0.0 --port $PORT
```

## Required environment variables

Railwayのサービス設定画面の Variables に次を設定してください。

- `RAILWAY_TOKEN`: 対象ワークスペースを読み取れるWorkspace Token
- `RAILWAY_WORKSPACE_ID`: `d72e603c-7a51-417e-984a-35edeb307cbf`

トークンはサーバー側の環境変数にだけ保存され、HTMLやブラウザへ返されません。公開ページ用に読み取り専用の権限で発行したトークンを使用してください。トークンをGitHubへコミットしないでください。

## Notes

- production環境を優先し、なければ先頭の環境を表示します。
- ステータスはRailway APIの最新デプロイ状態を基に分類します。
- 60秒間キャッシュし、ページ側も60秒ごとに更新します。
- 停止中は必ずしも障害を意味しません。
- APIトークンが未設定の場合、ページに初期設定が必要である旨だけを表示します。
