# WebSocket Handling

## Connecting
A ticket must be acquired by `GET /account/ticket`.

**Response**:
```json
{
  "success": "ticket created", 
  "data": {
    "token": "<generated ticket>"
  }
}
```

When connecting to the socket endpoint the ticket should be sent in the query string:
`WS /server/events?ticket=<generated ticket>`
TODO: Don't send ticket in query, is not encrypted. send it as a first client -> server message

## Packets
Packets are only sent server -> client, for data manipulation and query, the http endpoints of the API should be used.
A packet has the base structure:
```json
{
  "action": "ACTION",
  "data": {}
}
```

The "action" indicates the type of event that happened. The "data" depends on the action.

## Actions

### SERVER_STATE_CHANGE
Sent when some attributes of a server object change.

**Example**:
```json
{
  "action": "SERVER_STATE_CHANGE",
  "data": {
    "id": "607c71907be61b381db28144",
    "patch": {
      "onlineStatus": 1
    }
  }
}
```

### CONSOLE_LINE
Sent when a new line should be appended to the console output.

**Example**:
```json
{
  "action": "CONSOLE_LINE",
  "data": {
    "id": "607c71907be61b381db28144",
    "message": "New Console Message"
  }
}
```

### META_MESSAGE
The meta message contains messages that may be useful to developers but have no effect on the applications state.

**Example**:
```json
{
  "action": "META_MESSAGE",
  "data": {
    "message": "Use HTTP for data manipulation and query"
  }
}
```

### SERVER_ADD
Sent when a new server was created
"data" contains the new server object

**Example**:
```json
{
  "action": "SERVER_ADD",
  "data": {
  }
}
```

### ADDON_ADD
Sent when an addon got added to a server
"data.addon" contains the new addon object

**Example**:
```json
{
  "action": "ADDON_ADD",
  "data": {
    "serverId": "607c71907be61b381db28144",
    "addon": {}
  }
}
```

### ADDON_DELETE
Sent when an addon got removed from a server

**Example**:
```json
{
  "action": "ADDON_DELETE",
  "data": {
    "serverId": "607c71907be61b381db28144",
    "id": "addon id"
  }
}
```

### SERVER_DELETE
Sent when a new server was removed

**Example**:
```json
{
  "action": "SERVER_DELETE",
  "data": {
    "id": "607c71907be61b381db28144"
  }
}
```
