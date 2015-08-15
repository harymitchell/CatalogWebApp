from flask import Flask, render_template, url_for, request, redirect,flash,jsonify, make_response
app = Flask(__name__)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catalog, User, Item, Catagory
from flask import session as login_session
import random, string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests

engine = create_engine ('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

# Login
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state
    print CLIENT_ID
    return render_template('login.html', client_id = CLIENT_ID, STATE = state)

# Gconnect
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        print "invalid state parameter"
        flash ("invalid state parameter")
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        print 'Failed to upgrade the authorization code.'
        flash ('Failed to upgrade the authorization code.')
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        print "Token's user ID doesn't match given user ID."
        flash ("Token's user ID doesn't match given user ID.")
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        flash ("Token's client ID does not match app's.")
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        print 'Current user is already connected.'
        flash ("You were already connected.")
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    print login_session['picture']
    if not currentUser():
        header = "Welcome, "
        newUser = User(name = login_session['username'], image_uri = login_session['picture'])
        session.add(newUser)
        session.commit()
    else:
        header = "Welcome back, "

    output = ''
    output += "<h1> "+header
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        flash ("Current user not connected.")
        return catalog()
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash('Successfully disconnected')
        return catalog()
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        flash('Failed to revoke token for given user.')
        return catalog()

### catalog
@app.route('/')
@app.route('/index')
@app.route('/catalogs')
@app.route('/catalogs/<int:catalog_id>/')
@app.route('/catalogs/<int:catalog_id>/<int:catagory_id>')
def catalog(catalog_id=None,catagory_id=None):
    if not catalog_id:
        ## Default to catalog 1, since interface does not yet support switching.
        catalog_id = 1
    if session.query(Catalog).count() == 0:
        ## Create the default catalog, since interface does not yet support Catalog creation.
        ## Also, create a few default catagories, since interface does not support creating these.
        ## Create a test item to drive the demo
        ## Create Anonymous user
        catagoryA = Catagory (description="clothes")
        catagoryB = Catagory (description="sports")
        catagoryC = Catagory (description="electronics")
        new_catalog = Catalog (name = "catalogosphere")
        new_user = User(name = "Anonymous")
        new_item = Item (title = "Shirt",
                         content = "its awesome, its made out of synthetics.",
                         user = new_user,
                         catalog = new_catalog,
                         catagory= catagoryA)
        session.add (new_item)
        session.add (catagoryB)
        session.add (catagoryC)
        session.commit()
        print "test catalog content created..."
    catagoriesForId = session.query(Catagory).filter_by(id = catagory_id)
    catagory = None if catagoriesForId.count() < 1 else catagoriesForId.one()
    if catagory:
        searchCriteria = catagory.description
        items = session.query(Item).filter_by(catalog_id = catalog_id, catagory_id = catagory_id).all()
    else:
        searchCriteria = "Recently added items" 
        items = session.query(Item).filter_by(catalog_id = catalog_id).order_by("id desc").all()[:5]
    catalog = session.query(Catalog).filter_by(id = catalog_id).one()
    return render_template ('catalog.html', catalog_id = catalog_id, catalog = catalog, catagory_id = catagory_id, items = items, searchCriteria = searchCriteria, catagories = allCatagories(catalog), currentUser = currentUser())


### New item
@app.route('/catalogs/<int:catalog_id>/items/new', methods = ['GET', 'POST'])
@app.route('/catalogs/<int:catalog_id>/items/new/catagory/<int:catagory_id>', methods = ['GET', 'POST'])
def newitem(catalog_id, catagory_id=None):
    '''
        Returns template for adding new item on GET.
        On POST, will add the new item.
        If not logged in, will prompt for log in.
    '''
    print catagory_id
    catalog = session.query(Catalog).filter_by(id = catalog_id).one()
    if not currentUser():
        return redirect('/login')
    elif request.method == 'POST':
        catagory_id = request.form['catagory']
        newItem = Item(title = request.form['title'],
                       content = request.form['content'],
                       user_id = currentUserOrAnonymous().id,
                       catalog_id = catalog_id,
                       catagory_id = catagory_id)
        session.add(newItem)
        session.commit()
        flash("item "+newItem.title+" added successful!")
        return redirect(url_for('catalog', catalog_id=catalog_id, catalog=catalog, catagory_id=catagory_id))
    else:
        catagories = session.query(Catagory).filter_by(id=catagory_id)
        if catagories.count() == 1:
            print "found catagory"
            catagory_description = catagories.one().description
            return render_template('new_item.html', catagory_description = catagory_description, catalog_id = catalog_id, catalog=catalog, catagory_id = catagory_id, catagories = allCatagories(catalog), currentUser = currentUser())
        else:
            return render_template('new_item.html', catalog_id = catalog_id, catalog=catalog, catagory_id = catagory_id, catagories = allCatagories(catalog), currentUser = currentUser())
    
### Edit item
@app.route('/catalogs/<int:catalog_id>/items/<int:item_id>/edit', methods = ['GET', 'POST'])
def edititem (catalog_id, item_id):
    catalog = session.query(Catalog).filter_by(id = catalog_id).one()
    item = session.query (Item).filter_by (id=item_id).one()
    if not currentUser():
        return redirect('/login')
    elif item.user != currentUserOrAnonymous():
        flash("This item is not yours to edit!")
        return redirect(url_for('catalog', catalog_id = catalog_id, catalog=catalog))  
    elif request.method == 'POST':
        catagory_id = request.form['catagory']
        editItem = session.query(Item).filter_by(id = item_id).one()
        editItem.content = request.form['content']
        editItem.catagory = session.query(Catagory).filter_by(id=catagory_id).one()
        session.add(editItem)
        session.commit()
        flash("item updated!")
        return redirect(url_for('catalog', catalog_id = catalog_id, catalog=catalog))
    else:
        return render_template('edit_item.html', item_id = item_id, item = session.query(Item).filter_by(id=item_id).one(), catalog_id = catalog_id, catalog=catalog, catagories = allCatagories(catalog), currentUser = currentUser())
    
### View item
@app.route('/catalogs/<int:catalog_id>/items/<int:item_id>', methods = ['GET'])
def view_item (catalog_id, item_id):
    catalog = session.query(Catalog).filter_by(id = catalog_id).one()
    item = session.query (Item).filter_by (id=item_id).one()
    return render_template('view_item.html', item_id = item_id, item = session.query(Item).filter_by(id=item_id).one(), catalog_id = catalog_id, catalog=catalog, catagories = allCatagories(catalog), currentUser = currentUser())


### Delete item
@app.route('/catalogs/<int:catalog_id>/items/<int:item_id>/delete', methods = ['GET', 'POST'])
def deleteitem (catalog_id, item_id):
    catalog = session.query(Catalog).filter_by(id = catalog_id).one()
    item = session.query (Item).filter_by (id=item_id).one()
    if not currentUser():
        return redirect('/login')
    elif item.user != currentUser():
        flash("This item is not yours to delete!")
        return redirect(url_for('catalog', catalog_id = catalog_id, catalog=catalog))        
    elif request.method == 'POST':
        editItem = session.query(Item).filter_by(id = item_id).one()
        session.delete(editItem)
        session.commit()
        flash("item deleted!")
        return redirect(url_for('catalog', catalog_id = catalog_id, catalog=catalog))
    else:
        return render_template('delete_item.html', item_id = item_id, catalog_id = catalog_id, catalog=catalog, currentUser = currentUser())

### JSON of items
@app.route('/catalogs/<int:catalog_id>/items/JSON')
def catalogitems(catalog_id):
    catalog = session.query(catalog).filter_by(id = catalog_id).one()
    items = session.query(item).filter_by(catalog_id = catalog_id)
    return jsonify(catalogitems=[i.serialize for i in items])

def allCatagories(catalog):
    '''returns all catagories for catalog'''
    return session.query(Catagory)

def currentUser():
    ''' Returns the user currently logged in. '''
    if 'username' in login_session:
        users = session.query(User).filter_by(name=login_session['username'])
        if users.count() == 1:
            return users.one()

def currentUserOrAnonymous():
    ''' Returns the user currently logged in, or if none, the Anonymous user. '''
    l_user = currentUser()
    if l_user:
        return l_user
    else:
        users = session.query(User).filter_by(name='Anonymous').one()


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)
