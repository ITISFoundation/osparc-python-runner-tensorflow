# osparc-python-runner-tensorflow

oSparc Python Runner Tensorflow
![Github-CI](https://github.com/ITISFoundation/osparc-python-runner-tensorflow/workflows/Github-CI%20Push/PR%20osparc-python-runner-tensorflow/badge.svg)

## Description

oSparc service that allows running any python-based script either as simple script of complex python application inside a zip file (with or without requirements.txt file)


## Development

```console
make help                                # shows Makefile help

make devenv                              # creates python virtual environment
source .venv/bin/activate                # activates python virtual environment
make build                               # builds oSparc compatible docker image
make info-build                          # shows oSparc compatible docker image
make tests                               # tests oSparc compatible docker image
```

## CI/CD Integration

### Github-Actions

[github-ci.yml](https://github.com/ITISFoundation/osparc-python-runner-tensorflow/blob/master/.github/workflows/github-ci.yml)
