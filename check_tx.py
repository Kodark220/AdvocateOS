import urllib.request, json

data = json.dumps({
    "jsonrpc": "2.0",
    "method": "gen_getTransactionStatus",
    "params": [{"txId": "0x06b3e78bae600eb077aee51fe4f0f5a6d2871dbf8ff2070d3e599a1a700089e9"}],
    "id": 1
}).encode()

req = urllib.request.Request(
    "https://rpc-bradbury.genlayer.com",
    data=data,
    headers={"Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req).read().decode()
print(resp)

# Also get full receipt
data2 = json.dumps({
    "jsonrpc": "2.0",
    "method": "gen_getTransactionReceipt",
    "params": [{"txId": "0x06b3e78bae600eb077aee51fe4f0f5a6d2871dbf8ff2070d3e599a1a700089e9"}],
    "id": 2
}).encode()

req2 = urllib.request.Request(
    "https://rpc-bradbury.genlayer.com",
    data=data2,
    headers={"Content-Type": "application/json"}
)
resp2 = urllib.request.urlopen(req2).read().decode()
print(resp2)
