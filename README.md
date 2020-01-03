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

## directory tree

## Webhook

Adaptive Cardを使う場合、メッセージ用とは別に応答を受信するWebhookが別途必要になる。
typeで識別できるので、WebhookのターゲットURLは同じで構わない。

## Adaptive Cards

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

### Action.Submitの使い方

カードにはボタンをつけることができる。
ユーザがボタンを押すとwebhookを通して通知がくる。

messageIdキーでどのカードのボタンなのか、対応付けることができる。

ということは、カードを送ったときに返ってくるmessageIdキーを保存しておき、submitが返ってきたときにはどのmessageIdに対応したものなのか、調べる必要がある。
ある程度時間が経ったmessageIdは削除しないといけない。
それ以前にサーバが再起動すると消えちゃうのをなんとかしないと実用にはならないか。

## 参考文献

開発者向けのページ。
Bot用のアカウントを作ったり、APIのマニュアルを参照したり、何をするにしてもここがスタート地点。

<https://developer.webex.com/>

WebhookのAPIマニュアル

<https://developer.webex.com/docs/api/guides/webhooks>

アダプティブ カード

<https://docs.microsoft.com/ja-jp/adaptive-cards/authoring-cards/getting-started>