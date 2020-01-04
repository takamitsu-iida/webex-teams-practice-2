<!-- markdownlint-disable MD001 -->

# Cisco Webex Teamsの練習・その2

[Cisco Webex Teamsの練習・その1](https://github.com/takamitsu-iida/webex-teams-practice-1) の続きです。

今回はモジュール化する部分と、サーバ起動スクリプト、ボットロジック実装スクリプト、に分けています。

ngrokとredisが必要です。

## requirements

- gunicorn
- Flask
- requests
- dateutil
- pytz
- redis

## ブラウザで開くページ

[https://teams.webex.com/spaces](https://teams.webex.com/spaces)

[http://127.0.0.1:4040/inspect/http](http://127.0.0.1:4040/inspect/http)

[https://developer.webex.com/](https://developer.webex.com/)

## 起動と停止

### ngrokの起動とwebhook登録

`webhook.py --start`

一度実行すればngrokのプロセスは動き続けます。webhookも明示的に削除しない限り残ります。
ngrokを止めるとwebhookのステータスはdisabledになってしまうかもしれません。

`webhook.py --list`

ngrokとwebhookの状況を確認します。

`webhook.py --update`

webhookのステータスがdisabledになってしまった場合にactiveに戻します。一度disabledになってしまうと自動では戻りません。

### ngrokの停止とwebhookの削除

`webhook.py --kill`

ngrokを停止し、webhookを削除します。

`webhook.py --list`

ちゃんと消えたか、確認します。

### botサーバの起動

flaskに内蔵されているwsgiサーバを使うなら、

`server.py`

とします。

gunicornを使うなら、

`gunicorn -c ./conf/gunicorn.conf.py server:app`

とします。

いずれもCtrl-Cで停止します。

## Webhookについて

Adaptive Cardを使う場合、メッセージ用とは別に応答を受信するWebhookが必要になります。
つまり２個のWebhookを登録することになります。
受信したメッセージのtypeで識別できますので、WebhookのターゲットURLは同じで構いません。

## Adaptive Cardsについて

Cisco Webex TeamsでもMicrosoftのAdaptive Cardsが使えます。
ただし、全部の機能をサポートしているわけではありませんので、動くかどうかを試しながら実装するしかありません。

内容が静的なカードというのはあまり使いみちがなく、動的に生成するケースがほとんどでしょう。

Microsoftのテンプレートを使うとそのへんがうまく解決できるものの、
データとのバインディングはWebex Teamsでは実現できないようで、そのままでは使えません。

ここでは動的に値を差し替えたい部分をjinja2で処理することにします。

1. サンプルのJSONを持ってくる
1. そのJSONを加工して静的なカードにする
1. Webex Teamsに送ってみて形が期待通りに表示されることを確認する
1. jsonファイルをj2ファイルとしてコピーする
1. 動的に変更したい部分を"{{ }}"で置き換える
1. 実際に送信する前にJinja2で値を埋め込む

### Action.Submitの処理

カードにはボタンをつけることができます。
ユーザがボタンを押すとwebhookを通して通知がきます。

通知を受けたあと、内容を取りに行きます。
その内容にはmessageIdキーがありますので、それを使うことで、どのカードに対する応答なのか、対応付けられます。

カードを送ったときに返ってくるidキーを保存しておき、submitが返ってきたときにはどのカードに対応したものなのか、調べることになります。
カードの送信自体は多様なアプリで行われますので、保存先は外部のデータベースにしなければいけません。

ここではredisに保存することにします。
本当はREST APIを作って、それを経由してredisに保存するべきだと思いますが、直接redisに保存します。

## 参考文献

開発者向けのページ。
Bot用のアカウントを作ったり、APIのマニュアルを参照したり、何をするにしてもここがスタート地点。

<https://developer.webex.com/>

WebhookのAPIマニュアル

<https://developer.webex.com/docs/api/guides/webhooks>

アダプティブ カード

<https://docs.microsoft.com/ja-jp/adaptive-cards/authoring-cards/getting-started>
