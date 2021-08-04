test_data:
	cd tests \
	&& datalad install https://github.com/OpenNeuroDatasets/ds002080.git \
	&& cd ds002080 \
	&& datalad get sub-CON02/ses-postop/dwi

clean_test_data:
	chmod u+rw -R tests/ds002080 \
	&& rm -rf tests/ds002080

install:
	pip3 install . --user
	
upgrade:
	pip3 install . --user --upgrade