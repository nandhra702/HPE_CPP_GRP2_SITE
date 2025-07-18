WHAT ALL TO DO 

>>> FOR COPY-PASTE PREVENTION PART
go to site/django_ace/static/django_ace/

>> create 2 files : 
widget.css
widget.js






>>>> Install dolos globally. I use wsl, so I installed, like outside any directory.

Install from here -> https://dolos.ugent.be/docs/installation.html

next up, I have all the website files in this folder named 'site'. Refer to
the repositories I sent you. Make changes to following files in your system.


I have a submissions directory globally made by the name of "submissions". This is where the submissions 
are stored.

--> changes in contest-tab.html in site/templates/contest
 -->:Changes in ~/site/templates/contest >> show_similarity_table.html (create this file)
 --> changes in site/dmoj/urls.py
 --> changes in __init__.py in site/judge/views
 --> keep the script in site/judge/views (name of the file is trial_script.py 
 : the one which runs dolos)

 
 Further steps : 
 
 after changing the given files and changing respective addresses, start your virtual 
 environment. Go to /site directory where manage.py file is kept.
 
 /* CHECK manage.py AS A PRECAUTIONARY MEASURE FOR ANY CHANGES (like from my repo) */
 then, run : python manage.py runserver 0.0.0.0:8000
 
 (this is given that you have python3 installed in the venv)
 
 
