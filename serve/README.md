```
curl -X 'GET'   'http://localhost:8000/graph/neighbors/eth_transfers?k=2&limit=10'   -H 'accept: application/json'   -H 'Content-Type: application/json'   -d '["0x6e0d9c6dd8a08509bb625caa35dc61a991406f62","0xb877f7bb52d28f06e60f557c00a56225124b357f"]' -s -o /tmp/nexandria_out.json -w "\ndnslookup: %{time_namelookup} | connect: %{time_connect} | appconnect: %{time_appconnect} | pretransfer: %{time_pretransfer} | redirect: %{time_redirect} | starttransfer: %{time_starttransfer} | total: %{time_total} | size: %{size_download}\n"
```

```
$ cat /tmp/nexandria_in.txt
["0x6e0d9c6dd8a08509bb625caa35dc61a991406f62","0xb877f7bb52d28f06e60f557c00a56225124b357f"]

ab -v 4 -n 10 -c 5 -p /tmp/nexandria_in.txt -T 'application/json' http://127.0.0.1:8000/graph/neighbors/eth_transfers
```

