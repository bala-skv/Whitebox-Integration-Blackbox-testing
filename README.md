# ReadMe

This repository contains tests and code for three different modules/testing strategies:
1. **Integration Testing**
2. **Whitebox Testing**
3. **Blackbox Testing**

## How to run the Tests

Ensure you have `pytest` installed. You can run the tests for each module from the root directory (`2025121002`) using the following commands:

### 1. Integration Tests
```bash
PYTHONPATH=Integration/code/streetrace pytest -v -s Integration/tests/
```

### 2. Whitebox Tests
```bash
PYTHONPATH=Whitebox/code/moneypoly pytest -v Whitebox/tests/
```

### 3. Blackbox Tests
```bash
sudo docker load -i quickcart_image_x86.tar
sudo docker run -d -p 8080:8080 --name quickcart quickcart:latest

# 2. Install dependencies
pip install pytest requests

# 3. Run all tests
cd 2025121002/blackbox
python3 -m pytest tests/ -v
```

---

## How to run the Code

### 1. Integration Code (StreetRace)
To run the main implementation for the Integration module:
```bash
python3 Integration/code/streetrace/main.py
```

### 2. Whitebox Code (Moneypoly)
To run the main implementation for the Whitebox module:
```bash
python3 Whitebox/code/moneypoly/main.py
```


Github link : https://github.com/bala-skv/Whitebox-Integration-Blackbox-testing

OneDrive Link: 