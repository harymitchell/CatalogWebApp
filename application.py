from flask import Flask, render_template, url_for, request, redirect,flash,jsonify
app = Flask(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catalog, User, Item, Catagory

engine = create_engine ('sqlite:///catalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

### catalog
@app.route('/')
@app.route('/index')
@app.route('/catalogs')
@app.route('/catalogs/<int:catalog_id>/')
@app.route('/catalogs/<int:catalog_id>/<int:catagory_id>')
def catalog(catalog_id=None,catagory_id=None):
    ## Test data ##
    if not catagory_id:
        catagory_id = 1
    if session.query(Catalog).count() == 0:
        catagoryA = Catagory (description="clothes")
        catagoryB = Catagory (description="sports")
        catagoryC = Catagory (description="electronics")
        new_catalog = Catalog (name = "catalogosphere")
        new_user = User(name = "catalogomaniac")
        new_item = Item (content = "Shirt",
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
    result = render_template ('catalog.html', catalog_id = catalog_id, catalog = catalog, items = items, searchCriteria = searchCriteria, catagories = allCatagories(catalog))
    return result

### New item
@app.route('/catalogs/<int:catalog_id>/items/new', methods = ['GET', 'POST'])
@app.route('/catalogs/<int:catalog_id>/items/new/catagory/<int:catagory_id>', methods = ['GET', 'POST'])
def newitem(catalog_id, catagory_id=None):
    catalog = session.query(Catalog).filter_by(id = catalog_id).one()
    print "cat_id ", catagory_id
    if request.method == 'POST':
        catagory_id = request.form['catagory']
        print "catagory", catagory_id
        newItem = Item(content = request.form['content'],
                       user_id = 1,
                       catalog_id = catalog_id,
                       catagory_id = catagory_id)
        session.add(newItem)
        session.commit()
        flash("item "+newItem.content+" added successful!")
        return redirect(url_for('catalog', catalog_id=catalog_id, catalog=catalog))
    else:
        return render_template('new_item.html', catalog_id = catalog_id, catalog=catalog, catagory_id = catagory_id, catagories = allCatagories(catalog))
    
### Edit item
@app.route('/catalogs/<int:catalog_id>/items/<int:item_id>/edit', methods = ['GET', 'POST'])
def edititem (catalog_id, item_id):
    catalog = session.query(Catalog).filter_by(id = catalog_id).one()
    if request.method == 'POST':
        catagory_id = request.form['catagory']
        editItem = session.query(Item).filter_by(id = item_id).one()
        editItem.content = request.form['content']
        editItem.catagory = session.query(Catagory).filter_by(id=catagory_id).one()
        session.add(editItem)
        session.commit()
        flash("item updated!")
        return redirect(url_for('catalog', catalog_id = catalog_id, catalog=catalog))
    else:
        return render_template('edit_item.html', item_id = item_id, item = session.query(Item).filter_by(id=item_id).one(), catalog_id = catalog_id, catalog=catalog, catagories = allCatagories(catalog))

### Delete item
@app.route('/catalogs/<int:catalog_id>/items/<int:item_id>/delete', methods = ['GET', 'POST'])
def deleteitem (catalog_id, item_id):
    catalog = session.query(Catalog).filter_by(id = catalog_id).one()
    if request.method == 'POST':
        editItem = session.query(Item).filter_by(id = item_id).one()
        session.delete(editItem)
        session.commit()
        flash("item deleted!")
        return redirect(url_for('catalog', catalog_id = catalog_id, catalog=catalog))
    else:
        return render_template('delete_item.html', item_id = item_id, catalog_id = catalog_id, catalog=catalog)

### JSON of items
@app.route('/catalogs/<int:catalog_id>/items/JSON')
def catalogitems(catalog_id):
    catalog = session.query(catalog).filter_by(id = catalog_id).one()
    items = session.query(item).filter_by(catalog_id = catalog_id)
    return jsonify(catalogitems=[i.serialize for i in items])
    
def allCatagories(catalog):
    return session.query(Catagory)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 5000)
