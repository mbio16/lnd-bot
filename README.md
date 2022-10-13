# LND-bot

# INSTAL 

- download repo
    -   `git clone https://github.com/mbio16/lnd-bot.git`
- go inside folder:
    - ` cd lnd-bot`
- go inside certificate
    - cd certificate
    - copy tls.cert from lnd to this folder to validate self sign connection
- create .env file
    - `nano .env`
## .env params


**SIGNAL_RECIPIENTS** = ["+xxxxxxxxxxxx"] #number with number code such as +xxx
**SIGNAL_BASE_URL** = http://signal-client:8080 #if you want to use docker-compose variant, use this url
**SIGNAL_SOURCE_NUMBER**=+xxxxxxxxxx #sending signal number, has to be registered in later steps
**MACAROON** = xxxx #read only macaroon in hex format, can be obtained with `xxd -p -c 256 readonly.macaroon | tr -d '\n'`
**SAVE_CHANNEL_BACKUP**=True #if you want to save channel backup to db just in case to have another backup
**URL** = https://url:8080 #Rest port of your lnd node by default rest port is 8080
**VERIFY_CERT**=True #verify lnd cert 
**CERT_PATH**=./certificate/lnd.cert #path to lnd cert in repo, if you copy the lnd.cert from node, do not change path 
**POSTGRES_HOST**=postgres #db address, if you use docker-composem, do not change
**POSTGRES_PORT**=5432 # port, docker-compose do not change
**POSTGRES_PASSWORD**=xxxx #password to db for user, in docker compose it will create user with this password
**POSTGRES_USER**=ln # user to be created in db
**POSTGRES_DATABASE**=lnd_routing #db name to be created 
**LOG_FILE**=lndbot.log#filename to log, in docker container it will create file with this name
**LOG_LEVEL**=INFO #level to log, possible DEBUG,INFO,WARNIGN,ERROR

- start containers:
    - `docker-compose up -d`
## Setup Signal rest container with number
- after docker compose command, no message is sended, number has to be registered
- go to: [https://signalcaptchas.org/registration/generate.html](https://signalcaptchas.org/registration/generate.html)
    - complete catcha: get captcha `signalcaptcha://{captcha value} `
- `docker exec -ti lnd_bot-signal_client /bin/bash`
- `curl -X POST -H "Content-Type: application/json" -d '{"captcha":"captcha value"}' 'http://127.0.0.1:8080/v1/register/<SIGNAL_SOURCE_NUMBER>'`
- get text message to your SIGNAL_SOURCE_NUMBER
    - `curl -X POST -H "Content-Type: application/json" 'http://127.0.0.1:8080/v1/register/<SIGNAL_SOURCE_NUMBER>/verify/<VERIFICATION_CODE>'`¨
- test to send message: 
    - `curl -X POST -H "Content-Type: application/json" -d '{"message": "Test Message", "number": "SIGNAL_SOURCE_NUMBER", "recipients": ["SIGNAL_RECIPIENTS"]}' 'http://127.0.0.1:8080/v2/send'`
- `exit`

## cron scheduler
- Add crontab 
    - [https://crontab.guru/](https://crontab.guru/) - how often you want to run report
    - in your host
    - `crontab -e`
    - add `X X X X X docker start lnd_bot` where X X X X X is result generated from crontab.guru

# Report example
```
Date:     2022-10-11
Alias:    Node alias
Active channels:     20
Inactive channels:     0
------------------------------------
Date:         2022-10-11 14:39:26 
Inbound:     xx xxx xx 
Outbound:     xx xxx xx 
Onchain:     xx xxx 
Pending:     0 
------------------------------------
Summary all time:
------------------------------------
TXs:             x xxx
Routing [BTC]:     x xxx
Fee [sats]:     x xxx
------------------------------------
Summary yersterday:
------------------------------------
TX:             x
Routing [BTC]:     xxx
Fee [sats]:     xx

2022-10-10 xx:xx:xx: from 'name1' to 'name2' amount xx for fee x
2022-10-10 xx:xx:xx: from 'name1' to 'name2' amount xx for fee x
...
```