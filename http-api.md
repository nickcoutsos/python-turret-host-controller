# Turret Control Host API

## Configuration
`GET /configuration`

Return the configuration in use by this controller.


## Hosts
`GET /hosts`

Return a list of hosts being observed by this host.

`DELETE /hosts/<host>`

Disconnect from the specified `host`.


## Logs
`GET /logs`

Show a list of log entries recorded by this controller in reverse chronological
order.

Optional querystring parameters:

```
ARGUMENT           DEFAULT             DESCRIPTION
start              0                   Return log entries starting from <start>
rows               50                  Return the latest #<rows> entries.
level              DEBUG               Filter entries to <level> and higher.
```


## Turrets
`GET /turrets`

Return two lists:
* `controlled_turrets`: turrets under the control of this host.
* `visible_turrets`: turrets available to this host but are not in use.

Each list entry will follow this format:

```json
{
    "id": "string: unique to this host",
    "name": "string: human-readble identifier",
    "type": "string: type of turret (e.g. 'DC:Thunder')",
    "position": {
        "x": "float: x-offset of the turret (in meters) relative to zone origin",
        "y": "float: y-offset of the turret (in meters) relative to zone origin",
        "z": "float: z-offset of the turret (in meters) relative to zone origin"
    },
    "coverage": {
        "pitch": {
            "min": "float: lowest angle (in degrees) the turret can face",
            "max": "float: highest angle (in degrees) the turret can face"
        },
        "yaw": {
        }
    },
    "rockets": {
        "total": "int: number of rockets this turret can load at once",
        "remaining": "int: number of rockets ready to fire"
    }
}
```

Optional querystring parameters:

```
ARGUMENT           DEFAULT             DESCRIPTION
longpoll           false               Delay response until an update occurrs.
delay              0.0                 Wait <delay> msec for longpoll response.
```

In particular, the `delay` argument is useful for avoiding the overhead of 
high-frequency and low-importance updates.
