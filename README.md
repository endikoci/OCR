# OCR
 Optical Character Recognition converter

#pip install these///
/django
/redis
/celery
/pycairo
/python-doctr[tf] @ git+https://github.com/mindee/doctr.git
/reportlab>=3.6.2
/PyPDF2==1.26.0
/PyMuPDF



celery beat command >  celery -A OCR beat -l info
redis broker command > redis-server   
celery worker command > celery -A OCR worker -l info
run server command > python manage.py runserver

