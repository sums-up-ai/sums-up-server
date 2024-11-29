## How to run this script

1. Install virtualenv using the following command:
```bash
pip install virtualenv
```

2. Create a virtual environment using the following command:
```bash
virtualenv venv
```
or
```bash
python -m virtualenv venv
```

3. activate the virtual environment using the following command:
```bash
.\venv\Scripts\activate
```

4. Install the required packages using the following command:
```bash
pip install -r requirements.txt
```

5. Run the server with the following command:
```bash
uvicorn main:app --reload
```
