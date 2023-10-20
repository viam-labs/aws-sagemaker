module.tar.gz: requirements.txt .env *.sh src/*.py
	tar czf module.tar.gz $^
