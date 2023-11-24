lambda_applied: dep_pkg.zip
	terraform apply
	touch lambda_applied

dep_pkg.zip: denv
	cd denv/lib/python3.11/site-packages; zip -r ../../../../dep_pkg.zip .
	zip dep_pkg.zip gdu_calc.py

denv:
	python3.11 -m venv denv
	. denv/bin/activate; pip install requests;
		
install: 
	sudo apt update
	sudo apt install python3.11
	sudo apt install python3.11-dev python3.11-venv

test:
	. denv/bin/activate; python test_lambda_function.py $$(terraform output lambda-url)

clean:
	rm lambda_applied
	rm -rf denv
	rm -rf dep_pkg.zip
	terraform destroy