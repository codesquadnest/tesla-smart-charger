# Tesla Smart Charger

Dynamic charging control for your Tesla using the default charger and the Tesla API.


## Prerequisites
- Home server or Raspberry Pi with Git and Docker installed.
- Shelly EM (any equivalent energy monitor can be compatible with proper adaptation).
- Webserver like Nginx or Apache where you can host the public key and the callback URL.
- Tesla developer account.
- Tesla application.
- Tesla vehicle.

## Setup

This guide will help you to setup tesla-smart-charger on home server or Raspberry Pi.
The tesla-smart-charger aims to help Tesla owners to charge their vehicle when other
home appliances are in use so that the power consumption is optimized and without
overloading the electrical system.

The tesla-smart-charger uses the Tesla fleet API to get the vehicle state and send the
charging command to the vehicle.

### Tesla Fleet API access:
   
   Although the official documentation is available on the [Tesla API documentation](https://developer.tesla.com/docs/fleet-api/getting-started/what-is-fleet-api),
   this guide will the steps to setup the required authentication and configuration to
   use the tesla-smart-charger.
   
   
   **Setup tesla application**
   
   These instructions are based on the official [Tesla API documentation](https://developer.tesla.com/docs/fleet-api/getting-started/what-is-fleet-api).
   1. Go to [Tesla Developer](https://developer.tesla.com) website.
   2. Login with your Tesla account.
   3. Create a new application:
       - Fill the required fields.
       - Add your hostname where the public key and callback URL will be hosted.
       - Add the callback URL. The callback URL should be in the format `https://<hostname>/callback` (e.g. `https://example.com/done.html`).
       - Copy the client ID and client secret. You will need these to authenticate the tesla-smart-charger.
   4. Generate the private and public keys:
       - Go to the [Tesla Vehicle Command](https://github.com/teslamotors/vehicle-command) repository.
       - Use the tesla-keygen tool to generate the private and public keys:
   
       ```bash
       git clone https://github.com/teslamotors/vehicle-command.git
       cd vehicle-command/cmd/tesla-keygen
       go get ./...
       go build ./...
       ./tesla-keygen -key-file private-key.pem -keyring-type file create > public-key.pem
       ```
       - The public key should be hosted on the webserver.
       ```bash
       https://developer-domain.com/.well-known/appspecific/com.tesla.3p.public-key.pem
       ```
       - The private key should be kept secure and used to authenticate the tesla-smart-charger.
   
   5. Register the public key with the Tesla application:
       - In a web browser, go to the following URL:
       ```bash
       https://auth.tesla.com/oauth2/v3/authorize?&client_id=$CLIENT_ID&locale=en-US&prompt=login&redirect_uri=$CALLBACK_URL&response_type=code&scope=openid%20vehicle_device_data%20offline_access%20vehicle_cmds%20vehicle_charging_cmds&state=db4af3f87
       ```
       > Replace the `$CLIENT_ID` and `$CALLBACK_URL` with the values from the Tesla application.
   
       - Login with your Tesla account.
       - Copy the code from the URL and use it to register the public key:
       ```bash
       CLIENT_ID=$CLIENT_ID
       CLIENT_SECRET=$CLIENT_SECRET
       AUDIENCE="https://fleet-api.prd.eu.vn.cloud.tesla.com"
       CODE=$CODE
       # Partner authentication token request
       curl --request POST \
       --header 'Content-Type: application/x-www-form-urlencoded' \
       --data-urlencode 'grant_type=client_credentials' \
       --data-urlencode "client_id=$CLIENT_ID" \
       --data-urlencode "client_secret=$CLIENT_SECRET" \
       --data-urlencode 'scope=openid offline_access user_data vehicle_device_data vehicle_cmds vehicle_charging_cmds' \
       --data-urlencode "audience=$AUDIENCE" \
       'https://auth.tesla.com/oauth2/v3/token'
       ```
       - Copy the access token from the response and use it to register the public key:
       ```bash
       export TESLA_AUTH_TOKEN=$TOKEN
       curl -H "Authorization: Bearer $TESLA_AUTH_TOKEN" \
        -H 'Content-Type: application/json' \
        --data '{
                   "domain": "https://example.com",
               }' \
         -X POST \
         -i https://fleet-api.prd.eu.vn.cloud.tesla.com/api/1/partner_accounts
       ```
       - The public key should be registered with the Tesla application.
   
   6. Generate a self-signed certificate:
       - Generate a self-signed certificate for tesla-http-proxy:
       ```bash
       openssl req -x509 -nodes -newkey ec \
       -pkeyopt ec_paramgen_curve:secp521r1 \
       -pkeyopt ec_param_enc:named_curve  \
       -subj '/CN=localhost' \
       -keyout tls-key.pem -out tls-cert.pem -sha256 -days 3650 \
       -addext "subjectAltName = DNS:localhost" \
       -addext "extendedKeyUsage = serverAuth" \
       -addext "keyUsage = digitalSignature, keyCertSign, keyAgreement"
       ```
   
   7. Start the tesla-http-proxy:
       - The tesla-http-proxy is a reverse proxy that will forward the requests to the Tesla API.
       - Start the tesla-http-proxy:
       ```bash
       cd vehicle-command/cmd/tesla-http-proxy
       go build ./...
       # Copy cert.pem, key.pem, and private-key.pem to the same directory.
       ./tesla-http-proxy -tls-key tls-key.pem -cert tls-cert.pem -port 4443 -key-file private-key.pem -verbose
       ```
       - The tesla-http-proxy should be running on port 4443.
   
   8. Generate an OAuth token:
       - The OAuth token creation is also based on the official [Tesla Fleet API documentation](https://developer.tesla.com/docs/fleet-api/authentication/third-party-tokens):
       ```bash
       # Authorization code token request
       CLIENT_ID=$CLIENT_ID
       CLIENT_SECRET=$CLIENT_SECRET
       AUDIENCE="https://fleet-api.prd.eu.vn.cloud.tesla.com"
       CODE=$CODE # The code generated in step 5 or generate a new code using the same URL.
       CALLBACK="https://example.com/done.html"
       curl --request POST \
       --header 'Content-Type: application/x-www-form-urlencoded' \
       --data-urlencode 'grant_type=authorization_code' \
       --data-urlencode "client_id=$CLIENT_ID" \
       --data-urlencode "client_secret=$CLIENT_SECRET" \
       --data-urlencode "code=$CODE" \
       --data-urlencode "audience=$AUDIENCE" \
       --data-urlencode "redirect_uri=$CALLBACK" \
       'https://auth.tesla.com/oauth2/v3/token'
       # Extract access_token and refresh_token from this response
       ```
       - The access token and refresh token should be used to authenticate the tesla-smart-charger.
       - Refresh token expires in 3 months, to get a new refresh token, use the following command:
       ```bash
       # Refresh token request
       export REFRESH_TOKEN=$REFRESH_TOKEN
       export CLIENT_ID=$CLIENT_ID
       curl --request POST \
       --header 'Content-Type: application/x-www-form-urlencoded' \
       --data-urlencode 'grant_type=refresh_token' \
       --data-urlencode "client_id=$CLIENT_ID" \
       --data-urlencode "refresh_token=$REFRESH_TOKEN" \
       'https://auth.tesla.com/oauth2/v3/token'
   
   9. The Tesla application is now setup and ready to be tested with the tesla-http-proxy:
       - Test the Tesla application with the tesla-http-proxy:
       ```bash
       export TESLA_AUTH_TOKEN=$OAuth_TOKEN
       export VIN=$VIN
       curl --cacert tls-cert.pem \
           --header "Authorization: Bearer $TESLA_AUTH_TOKEN" \
           "https://localhost:4443/api/1/vehicles/$VIN/vehicle_data" \
           | jq -r .
   
       # The response should be the vehicle data.
       ```
   
   > The Tesla application is now setup and ready to be used with the tesla-smart-charger.
   

### Configuration:
   
   From the previous steps, you should have the following information:
   - `client_id`
   - `client_secret`
   - `public_key.pem`
   - `private_key.pem`
   - `access_token`
   - `refresh_token`
   - `VIN`


   Fill the configuration `config.json` with your specific values:
   - `homeMaxAmps`: Available power in amps that is available for the house.
   - `chargerMaxAmps`: Maximum power in amps that the charger can use.
   - `chargerMinAmps`: Minimum power in amps that the charger can use.
   - `downStepPercentage`: Percentage of power reduction when overload is detected.
   - `upStepPercentage`: Percentage of power increase when overload is not detected.
   - `sleepTimeSecs`: Time in seconds between each check after overload is detected.
   - `energyMonitorIp`: IP address or hostname of the Energy Monitor.
   - `energyMonitorType`: Type of Energy Monitor. Currently only `shelly-em` is supported.
   - `hostIp`: IP address of the host machine. This is used to send overload notifications to the Energy Monitor thread.
   - `apiPort`: Port where the Tesla Smart Charger API will be exposed.
   - `teslaVehicleId`: Vehicle ID obtained from the Tesla API.
   - `teslaAccessToken`: Access token obtained from the Tesla API.
   - `teslaRefreshToken`: Refresh token obtained from the Tesla API.
   - `teslaHttpProxy`: HTTP proxy to use when connecting to the Tesla API.
   - `teslaClientId`: Client ID obtained from the Tesla API.

   The configuration file is located at `config.json` and should look like this:
   ```json
   {
      "homeMaxAmps": 30.0,
      "chargerMaxAmps": 25.0,
      "chargerMinAmps": 6.0,
      "downStepPercentage": 0.5,
      "upStepPercentage": 0.25,
      "sleepTimeSecs": 20,
      "energyMonitorIp": "ip-or-hostname",
      "energyMonitorType": "shelly-em",
      "hostIp": "ip-address",
      "apiPort": 8000,
      "teslaVehicleId": "12345678901234567",
      "teslaAccessToken": "12345678901234567",
      "teslaRefreshToken": "12345678901234567",
      "teslaHttpProxy": "http://localhost:4443",
      "teslaClientId": "12345678901234567"
   }

   **Notes:**
      - Choose values wisely
      - When assigning a different port, make sure to update the `Dockerfile`
         and set the `apiPort` port in `config.json` to the same value.
   ```


3. **Energy monitor configuration:**
   Configure your Energy Monitor to hit the `<tesla-smart-charger>/overload` endpoint when power consumption goes above the configured limit.

   #### Local Energy Monitor Option
   Alternatively, you can use the `tesla-smart-charger` `--monitor` option to monitor the power consumption and trigger the overload endpoint when the configured limit is exceeded.

   ```bash
   tesla-smart-charger --monitor
   ```

   **Note:** The `--monitor` option requires the `energyMonitorIp` and `hostIp` to be set in the `config.json` file.


4. **Execution:**
   Run the Tesla Smart Charger:
   ```bash
   docker compose up -d
   ```

   To test your configuration you can call (GET) `<tesla-smart-charger>/config`

   The default behavior, with no extra configuration, is that the charging amps will be reduced by the `downStepPercentage` configuration. For example, if `downStepPercentage` is set to 0.5, the charging amps will be configured to half of the current amps. If it's set to 0.25, it will be configured to 25% of the current amps.

   Importantly, Tesla Smart Charger will never send wake-up commands to the car. It will only be triggered when the car is online and charging. It's not expected to cause any battery drains.

5. **Dynamic Charging Sessions:**
   The to-do section includes the configuration of dynamic charging sessions triggered when an overload is detected. To achieve this, a power monitor, such as Shelly EM, is required to fetch current power consumption.

## How to Contribute

We welcome contributions to enhance the functionality and features of Tesla Smart Charger. If you're interested in contributing, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Implement your changes.
4. Test your changes thoroughly.
5. Create a pull request with a clear description of your changes.

## Features

- **Charging Control:**
  - The Tesla Smart Charger allows dynamic control of charging parameters based on the configured settings.

Feel free to contribute and help make Tesla Smart Charger even better!
