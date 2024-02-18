```
curl -X 'GET'   'http://localhost:8000/scores/neighbors/eth?k=5&limit=100'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x6e0d9c6dd8a08509bb625caa35dc61a991406f62","0xb877f7bb52d28f06e60f557c00a56225124b357f", "0xbfa141e93226263cdde4cd5c847879205443b1a2"]' -s -o /tmp/nexandria_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"

curl -X 'GET'   'http://localhost:8000/scores/neighbors/eth?k=5&limit=100'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0xbfa141e93226263cdde4cd5c847879205443b1a2"]' -s -o /tmp/nexandria_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"

curl -H "API-Key:$NEXANDRIA_API_KEY" 'https://api.nexandria.com/eth/v1/address/0x6e0d9c6dd8a08509bb625caa35dc61a991406f62/neighbors?from_ts=1672560000&to_ts=1704096000&allow_cp=0x6e11861f0286a0406ca652e3b6d3a1216bc90345' | json_pp

curl -H "API-Key:$NEXANDRIA_API_KEY" 'https://api.nexandria.com/eth/v1/address/0x6e0d9c6dd8a08509bb625caa35dc61a991406f62/neighbors?from_ts=1672560000&to_ts=1704096000&allow_cp=0x6e11861f0286a0406ca652e3b6d3a1216bc90345&details=summary' | json_pp
```

```
$ cat /tmp/nexandria_in.txt
["0x6e0d9c6dd8a08509bb625caa35dc61a991406f62","0xb877f7bb52d28f06e60f557c00a56225124b357f"]

ab -v 4 -n 10 -c 5 -p /tmp/nexandria_in.txt -T 'application/json' http://127.0.0.1:8000/graph/neighbors/eth_transfers
```

