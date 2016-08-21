# flocker-rest-client

Flexible Flocker REST API Client in pure Python3 with no external dependencies. The whole script runs from CLI and dynamically handles parameter parsing so that it can easily be modified and extended

## Examples

- `CERT_DIR=. ./flocker_api.py create_volume --profile gold foo 5 some-uuid`
- `CERT_DIR=. ./flocker_api.py list_volumes`
- `CERT_DIR=. ./flocker_api.py delete_volume f400108c-2ae5-42fc-822e-f41b0680d0fd`

## Dynamic help

Function:
```
@cli_method
def create_volume(self, name, size_in_gb, primary_id, profile = None):
"""
Creates a volume by attaching it to the specified node of the given size.
Profile may be provided to specify IOPS.
"""
```

turns into:

```
$ CERT_DIR=. ./flocker_api.py -h
usage: flocker_api.py [-h]
    ...
    create_volume       Creates a volume by attaching it to the specified node
                        of the given size. Profile may be provided to specify
                        IOPS. . See "create_volume -help" for more options
```

and

```
$ CERT_DIR=. ./flocker_api.py create_volume
usage: flocker_api.py create_volume [-h] [--profile PROFILE]
                                    name size_in_gb primary_id
flocker_api.py create_volume: error: the following arguments are required: name, size_in_gb, primary_id
```

## License

LGPLv2

## Maintainers

- Srdjan Grubor <sgnn7@sgnn7.org>
