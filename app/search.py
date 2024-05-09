from flask import current_app, flash, render_template, request
from db import db_session

@current_app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        search_string = request.form['search_str']
        error = None
        
        if not search_string:
            error = 'Please provide a search string'
        
        if error is None:
            do_search()
        
        flash(error)
    
    return render_template('search.html')