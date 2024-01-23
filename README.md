# Tesla Smart Charger

Dynamic charging control for your Tesla using the default charger.

## Usage

1. **Installation:**
   ```bash
   pip install poetry
   poetry install
   ```

2. **Configuration:**
   
   Fill the configuration with your specific settings:
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
      "teslaRefreshToken": "12345678901234567"
   }

   **Notes:**
      - Choose values wisely
      - When assigning a different port, make sure to update the `Dockerfile`
         and set the `apiPort` port in `config.json` to the same value.

   
   ```
   Make sure to obtain the required tokens by following the instructions [here](https://github.com/adriankumpf/tesla_auth).

   Get your vehicle ID by executing the following command:
   ```bash
   tesla-smart-charger vehicles
   ```


3. **Energy monitor configuration:**
   Configure your Energy Monitor to hit the `<tesla-smart-charger>/overload` endpoint when power consumption goes above the configured limit.

   #### Local Energy Monitor Option
   Alternatively, you can use the `tesla-smart-charger` `--monitor` option to monitor the power consumption and trigger the overload endpoint when the configured limit is exceeded.

   ```bash
   tesla-smart-charger --monitor
   ```


4. **Execution:**
   Run the Tesla Smart Charger:
   ```bash
   tesla-smart-charger
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

## To-Do

- Implement additional features and improvements, including the configuration of dynamic charging sessions when overload is triggered.

## Requirements

- Energy monitor like Shelly EM or equivalent.
- Trigger mechanism to hit the `<tesla-smart-charger>/overload` endpoint.
- Any machine to execute Tesla Smart Charger.

## Running with Docker

1. **Build Docker Image:**
   ```bash
   docker build -t tesla-smart-charger .
   ```
2. **Get Vehicle ID:**
   ```bash
   docker run -it --rm -v ${PWD}:/app tesla-smart-charger:latest tesla-smart-charger vehicles
   ```  
3. **Run Docker Container:**
   ```bash
   docker run -it -p 8000:8000 -v ${PWD}:/app -d --restart unless-stopped --name tesla tesla-smart-charger:latest
   ```

Feel free to contribute and help make Tesla Smart Charger even better!
