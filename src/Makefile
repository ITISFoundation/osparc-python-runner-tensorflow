
osparc_python_runner_tensorflow/requirements.txt: requirements.in _check_venv_active
	# Updating $@
	pip-compile --upgrade --build-isolation --output-file $@ $<


.PHONY: _check_venv_active
_check_venv_active:
	# checking whether virtual environment was activated
	@python3 -c "import sys; assert sys.base_prefix!=sys.prefix"