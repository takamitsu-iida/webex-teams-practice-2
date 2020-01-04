<!-- markdownlint-disable MD001 -->

# Cisco Webex Teamsの練習・その2

[Cisco Webex Teamsの練習・その1](https://github.com/takamitsu-iida/webex-teams-practice-1) の続きです。

## requirements

- gunicorn
- Flask
- requests
- dateutil
- pytz
- redis

## ブラウザで開くべきページ

[https://teams.webex.com/spaces](https://teams.webex.com/spaces)

[http://127.0.0.1:4040/inspect/http](http://127.0.0.1:4040/inspect/http)

[https://developer.webex.com/](https://developer.webex.com/)

## 起動と停止

### ngrokの起動とwebhook登録

`webhook.py --start`

一度実行すればngrokのプロセスは動き続ける。webhookも明示的に削除しない限り残る。

`webhook.py --list`

ngrokとwebhookの状況を確認する。

`webhook.py --update`

webhookのステータスがdisabledになってしまった場合にactiveに戻す。自動では戻らない。

### ngrokの停止とwebhookの削除

`webhook.py --kill`

ngrokを停止し、webhookを削除する。

`webhook.py --list`

ちゃんと消えたか、確認する。

### botサーバの起動

flaskのwsgiサーバを使うなら、

`server.py`

gunicornを使うなら、

`gunicorn -c ./conf/gunicorn.conf.py server:app`

いずれもCtrl-Cで停止する。

## Webhookについて

Adaptive Cardを使う場合、メッセージ用とは別に応答を受信するWebhookが必要になる。
typeで識別できるので、WebhookのターゲットURLは同じで構わない。

## Adaptive Cardsについて

Cisco Webex TeamsでもMicrosoftのAdaptive Cardsが使える。
ただし、全部の機能をサポートしているわけではないので、動くかどうかを試しながらやるしかない。

内容が静的なカードというのはあまり使いみちがなく、動的に生成しないといけない。
Microsoftのテンプレートを使うとそのへんがうまく解決できるものの、
データとのバインディングをどうやって処理するのか、いまいち分からない。

動的に値を差し替えたい部分をjinja2で処理することにする。

1. サンプルのJSONを持ってくる
1. そのJSONを加工して静的なカードにする
1. Webex Teamsに送ってみて形が期待通りに表示されることを確認する
1. jsonファイルをj2ファイルにコピーする
1. 実際に送信するまえにJinja2で値を埋め込む

### Action.Submitの処理

カードにはボタンをつけることができる。
ユーザがボタンを押すとwebhookを通して通知がくる。

messageIdキーでどのカードに対する応答か、対応付けできる。

カードを送ったときに返ってくるidキーを保存しておき、submitが返ってきたときにはどのカードに対応したものなのか、調べる必要がある。
カードの送信自体は多様なアプリで行われるので、保存先は外部のデータベースにするのがよい。
ここではredisに保存している。

## 参考文献

開発者向けのページ。
Bot用のアカウントを作ったり、APIのマニュアルを参照したり、何をするにしてもここがスタート地点。

<https://developer.webex.com/>

WebhookのAPIマニュアル

<https://developer.webex.com/docs/api/guides/webhooks>

アダプティブ カード

<https://docs.microsoft.com/ja-jp/adaptive-cards/authoring-cards/getting-started>
