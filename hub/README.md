# Inference Router

Inference router allows you to run complex inference based on your request.

It supports multiple providers and can be easily extended to support more. Supported inference providers: [Link](https://github.com/nearai/inference-router/blob/2bd1ab88d52c345b9796813fe9f6dfcca43dbcd4/api/v1/completions.py#L12)

## Inference Router API setup

```
python -m venv venv
source venv/bin/activate
pip install -e .
```

Start the dev server with:

```
fastapi dev app.py --port 8081
```

Start production server with:

```
fastapi run app.py --port 8081
```

## Frontend

```
cd ./demo
npm install
```

Start dev frontend with:

```
npm run dev
```

Start production frontend with:

```
npm run start
```
