Save generated certificate files in this directory.

## Generate certificates

```bash
    git clone https://github.com/teslamotors/vehicle-command.git
    cd vehicle-command/cmd/tesla-keygen
    go get ./...
    go build ./...
    ./tesla-keygen -key-file private-key.pem -keyring-type file create > public-key.pem
```

The public key should be hosted on the webserver.

```bash
    https://developer-domain.com/.well-known/appspecific/com.tesla.3p.public-key.pem
```