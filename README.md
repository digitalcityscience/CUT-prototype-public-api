# CUT Prototype Public API

A FastAPI-based API that acts as a `reverse proxy`, forwarding requests to different target servers (noise. water, wind, pedestrians) based on the requested endpoint's path. It also centralises the following features:
1) rate limiting; 
2) authorization; 
3) request event metadata logging by user;
4) `CORS` support;
5) response format conversion (PNG, geojson).

!["CUT Prototype Architecture"](.documentation/cut-architecture.jpg "CUT Prototype Architecture")


## Local Dev

### Initial Setup

The `CUT Prototype Public API` is run on `Docker`, however it is still necessary to create a `Python` virtual environment to run tests, run a script to create internal users and enable linting for pre-commit hooks. Run the following command to set up your environment: 


```
$ make create-env
```

This command will create a virtualenv, install all dependencies including pre-commit hooks and create a `.env` file based on `./.env.example`. 

After the command runs, make sure to adapt your `.env` file with secure secrets, etc.  If your `IDE` does not activate your virtualenv automatically, run: 

```
$ source .venv/bin/activate
```

> [!IMPORTANT]
> This repository uses `Makefile` to run commands, in case you can't use Make, just run the correspondent commands as in [this file](./Makefile).


### Starting the services 

To start the services using `Docker`, simply run: 

```
$  make start
```

After the image is built and containers initialise, you can access the following in your browser: 

| Service    | URL                              | Access                                      |
|------------|----------------------------------|---------------------------------------------|
| Swagger UI | http://0.0.0.0:8008/docs         | Not password protected                       |
| Redoc      | http://0.0.0.0:8008/redoc        | Not password protected                       |

### Formating/ linting code

```
$ make fmt
```

```
$ make lint
```


## Tests 

```bash
make test
```