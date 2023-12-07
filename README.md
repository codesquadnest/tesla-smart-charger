# Tesla Smart Charger

Dynamic charging control for your Tesla using the default charger.

## Usage

1. **Installation:**
   ```bash
   pip install poetry
   poetry install
   ```

2. **Configuration:**
   Edit the `config.json` file with your specific settings:
   ```json
   {
       "maxPower": "20.0",
       "minPower": "0.0",
       "downStep": "0.5",
       "upStep": "0.1",
       "sleepTime": "300",
       "vehicleId": "vehicleId",
       "accessToken": "accessToken",
       "refreshToken": "refreshToken"
   }
   ```
   Make sure to obtain the required tokens by following the instructions [here](https://github.com/adriankumpf/tesla_auth).

   While we don't implement an automated way to get VehicleID use the following ref [here]([https://github.com/adriankumpf/tesla_auth](https://developer.tesla.com/docs/fleet-api?shell#list)).


3. **Energy monitor configuration:**
   Configure you Energy Monitor to hit the `<tesla-smart-charger>/overload` endpoint when power consumption goes above the configured limit.

4. **Execution:**
   Run the Tesla Smart Charger:
   ```bash
   tesla-smart-charger
   ```

   To test your configuration you can call (GET) `<tesla-smart-charger>/config`

   The default behavior, with no extra configuration, is that the charging amps will be reduced by the `downStep` configuration. For example, if `downStep` is set to 0.5, the charging amps will be configured to half of the current amps. If it's set to 0.25, it will be configured to 25% of the current amps.

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
   docker build -t tesla-smart-charger:v1 .
   ```

2. **Run Docker Container:**
   ```bash
   docker run --rm -it -p 8000:8000 tesla-smart-charger:v1
   ```

Feel free to contribute and help make Tesla Smart Charger even better!
