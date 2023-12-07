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
       "maxPower": "5.0",
       "minPower": "0.0",
       "downStep": "0.5",
       "upStep": "0.1",
       "sleepTime": "300",
       "vehicleId": "1234567890",
       "accessToken": "1234567890",
       "refreshToken": "0987654321"
   }
   ```
   Make sure to obtain the required tokens by following the instructions [here](https://github.com/adriankumpf/tesla_auth).

3. **Execution:**
   Run the Tesla Smart Charger:
   ```bash
   tesla-smart-charger
   ```

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

- Implement additional features and improvements.

## References

1. [Tesla API Lite](https://github.com/Marky0/tesla_api_lite)
2. [Tesla Auth](https://github.com/adriankumpf/tesla_auth)

Feel free to contribute and help make Tesla Smart Charger even better!
