from flask import Flask
from markupsafe import escape
from flask import url_for
from flask import render_template
from flask import g
from flask import request
from flask import redirect
from flask import abort
from flask import session
from werkzeug.security import generate_password_hash, check_password_hash
import shutil
import functools
import os
import sqlite3
#imports all the required flask and other libs
app = Flask(__name__) #Only use one module so __name__ is instead of __main__
UPLOAD_FOLDER = r"D:\School\Cov\Year 2\Project\static\images\book-images"   #This is where we save the book covers
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = "secret key" #defines the secret key

@app.before_request #This will load first, as we require user to be logged in
def user_login():
    userID = session.get('userName') #this will get the user from the session userName, 
    if userID is None:               #if it is empty then we know no one is logged in
        g.user = None                #g.user is a global variable   
    else:
        g.user = 'set'

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs): #if it is determined their no user, it will load the login url
        if g.user is None: #this function will loop itself until their is a login
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view


@app.route('/login', methods=['GET', 'POST']) #this is the login functions
def login():
    if request.method == 'POST': #once it recieves information from the login submition it passes it to do_login
        return do_login(request.form['userName'],request.form['password'])
    else:
        return show_login_page() #if not it loads the login page
def show_login_page():
    return render_template('login.html',page=url_for('login')) #loads login page
def do_login(userN,passW):
    formatUserInfo = userN + "," + passW #format the given username and password from submit form
    userName = "user"
    admin = "admin"
    session['userName'] = userName #creates the regular and admin user session
    session['admin'] = admin
    if 'userName' in session: #pops both session so we make sure it doesnt think the user is logged in yet
        session.pop('userName',None)
    if 'admin' in session:
        session.pop('admin',None)
    con = sqlite3.connect('mydatabase.db') #we connect to the database, and pull the username and password from user table
    cur=con.cursor()
    cur.execute("SELECT userName,password FROM user")
    userInfo = cur.fetchall()
    for user in userInfo:#loops through all the users pulled from table
        user=str(user).replace("(","") #fetchall brings it as a tuple so we want to make sure its in the correct format when comparing the values
        user=str(user).replace(")","")
        user=str(user).replace("'","")
        user=str(user).replace(" ","")
        if user == formatUserInfo: #we then compare our values from the table, to values from submission form
            if userN == 'admin': #if the username was admin we know this is an admin user and we activate both sessions
                session['userName'] = userName
                session['admin'] = admin
                return redirect("http://127.0.0.1:5000/") #we then send it to the homepage
            else:
                session['userName'] = userName #is not admin so only user session
                return redirect("http://127.0.0.1:5000/")
    else:
        return redirect(url_for('login')) #loops if password or username was wrong
@app.route('/logout') #logs the user out
def logout():
    session.clear() #this will clear all the current sessions
    return redirect(url_for('login'))



@app.route('/') #this is the homepage
@login_required #user must be logged in to accesss
def book():
    try:
        con = sqlite3.connect('mydatabase.db')#connects to database and pulls all the information from books table
        cur = con.cursor();
        cur.execute("SELECT * FROM books")
        rows = cur.fetchall()
        return render_template('homepage.html', book=rows)#sends this info to table in homepage to load books
    except Exception as e:#prints any expections
        print(e)
    finally:
        cur.close() #closes the connection to the database
        con.close()

@app.route('/home', methods=['GET', 'POST'])  #simply a test for development, unused in website
@login_required
def books_get():
    con = sqlite3.connect("mydatabase.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute('SELECT bookName, image FROM books WHERE quant > 0')
    row = cur.fetchall()
    return render_template('home.html', rows = row)


@app.route("/create")  #this was used to create the tables 
@login_required
def create():
    con = sqlite3.connect('mydatabase.db') #if the table does not exist it will create a table called books with 9 coloumns
    try:
        con.execute('CREATE TABLE IF NOT EXISTS books(\
            bookName TEXT, \
            author TEXT,\
            pubDate TEXT, \
            ISBN INT, \
            desc TEXT, \
            traVal INT, \
            retPrice INT, \
            quant INT, \
            image TEXT)')
            #creates user table if it doesnt exist with 2 coloumns
        con.execute('CREATE TABLE IF NOT EXISTS user(\
            userName TEXT, \
            password TEXT)')
    except: #if they exist nothing happens
        pass
    con.close()
    return redirect(url_for('.book'))#returns to homepage after

@app.route("/addBook", methods=['GET', 'POST'])#This will add books and update the stock
@login_required #requires user to be logged in
def addBook():
    if request.method == 'POST':
        ISBN = request.form['ISBN'] #gets the isbn given by user in form
        quant = request.form['quant'] #gets the quantity given by user in form
        con = sqlite3.connect('mydatabase.db')
        cur = con.cursor();
        cur.execute("SELECT ISBN FROM books") #this will be used to check if book already exists
        isbnNum = cur.fetchall()
        for book in isbnNum: #loops through all isbn numbers in book table
            book=str(book).replace("(","")#formats it into useable format
            book=str(book).replace(")","")
            book=str(book).replace(",","")
            book=str(book).replace("'","")
            if book == ISBN: #comapres the isbn number to the one given in the form
                cur.execute("SELECT quant FROM books WHERE ISBN = '" + ISBN + "'") #if it matches we then pull the quantity that matches that isbn
                curQuant = cur.fetchall()
                curQuant=str(curQuant[0]).replace("(","") #format it into a useable state
                curQuant=curQuant.replace("(","")
                curQuant=curQuant.replace(")","")
                curQuant=curQuant.replace("'","")
                curQuant=curQuant.replace(",","")
                newQuant = int(curQuant) + int(quant) #we add old quantity to new quantity
                cur.execute("UPDATE books SET quant = " + str(newQuant) + " WHERE ISBN = '" + ISBN + "'") #updates quantity in table
                con.commit() #commits changes
                return show_add_book()#goes back to stock levels
        
        if 'image' not in request.files: #requires an image for the book table
            return 'there is no image in form!'
        image = request.files['image']#pulls image from form
        path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)#connects image to the UPLOAD_FOLDER
        imageName = image.filename #assign a variable with the same name as the image file
        image.save(path)#saves the image to the given path
        return add_book(request.form['bookName'],request.form['author'],request.form['pubDate'],request.form['ISBN'], request.form['desc'],request.form['traVal'],request.form['retPrice'],request.form['quant'],imageName)
    else:
        return show_add_book()
def show_add_book():
    return render_template('addBook.html',page=url_for('addBook'))#loads the add book page
def add_book(bookName, author, pubDate, ISBN, desc, traVal, retPrice, quant,image):
    con = sqlite3.connect('mydatabase.db')
    cur = con.cursor(); #if the book does not exist this will insert the values from the form into the book tables

    sql = "INSERT INTO books(bookName, author, pubDate, ISBN, desc, traVal, retPrice, quant,image) VALUES (?,?,?,?,?,?,?,?,?)"
    #con.execute("INSERT INTO books(bookName, author, pubDate, ISBN, desc, traVal, retPrice, quant) VALUES (?,?,?,?,?,?,?,?)",[bookName, author, pubDate, ISBN, desc, traVal, retPrice, quant])
    val = (bookName, author, pubDate, ISBN, desc, traVal, retPrice, quant,image)
    cur.execute(sql,val) #executes the query with given variables
    con.commit()#saves changes
    con.close()
    return show_add_book()

@app.route('/showBooks')# this was simply useded for testing, shows all books
@login_required
def showBooks():
    con = sqlite3.connect('mydatabase.db')
    con.row_factory = sqlite3.Row
    cur=con.cursor()
    cur.execute("SELECT * FROM books")
    row = cur.fetchall()
    return render_template('books.html', rows = row)

@app.route('/showStock') #this will show the user the current stock in the table
@login_required
def showStock():
    con = sqlite3.connect('mydatabase.db')
    con.row_factory = sqlite3.Row
    cur=con.cursor()
    cur.execute("SELECT * FROM books")
    row = cur.fetchall()
    return render_template('stock.html', rows = row)#sends it to the stock page

@app.route('/add', methods=['POST'])
@login_required
def add_product_to_cart():#this will add the books to the shopping cart
    cursor = None
    try:
        _quant = int(request.form['quant']) #gets the quantity and the the ISBN from the form
        _ISBN = request.form['ISBN']
        
        if _quant and _ISBN and request.method == 'POST':
            con = sqlite3.connect('mydatabase.db') #once these values are gotten, and the user has picked a book, we get all the info on that book
            cur = con.cursor()
            cur.execute("SELECT * FROM books WHERE ISBN=?;", [_ISBN]) #pulls book that match isbn
            row = cur.fetchone()#only pulls the one row
            itemArray = { row[4] : {'bookName' : row[0], 'ISBN' : row[3], 'quant' : _quant, 'retPrice' : row[6], 'image' : row[8], 'total_price': _quant * row[6]}}
            print('itemArray is', itemArray) #this creates an item array based on the given info
            
            all_total_price = 0 #defines the variables, total price and quantity for the cart session
            all_total_quantity = 0
            
            session.modified = True
            
            if 'cart_item' in session: #if the cart item session exists then this runs
                print('in session')
                if row[0] in session['cart_item']: #if it has an isbn in the cart item session
                    for key, value in session['cart_item'].items(): #loops through the cart items
                        if row[0] == ['cart_item'][key]['ISBN']: #if the isbn matches the key
                            old_quantity = session['cart_item'][key]['quant'] #pulls the quantity from the cart session
                            total_quantity = old_quantity + _quant #adds the quantity to the total quantity
                            session['cart_item'][key]['quant'] = total_quantity #updates total quantity in session
                            session['cart_item'][key]['total_price'] = total_quantity * row[6] #updates the price in session using the retail price
                else:
                    session['cart_item'] = array_merge(session['cart_item'], itemArray) #sends to the array merge
                    
                for key, value in session['cart_item'].items():
                    individual_quantity = int(session['cart_item'][key]['quant']) #defines the quantity from the value inside session
                    individual_price = float(session['cart_item'][key]['total_price'])#defiens the total price of a book from session
                    all_total_quantity = all_total_quantity + individual_quantity #calculates total
                    all_total_price = all_total_price + individual_price
            else:
                session['cart_item'] = itemArray #if the session doesnt already exist this creates 
                all_total_quantity = all_total_quantity + _quant
                all_total_price = all_total_price + _quant * row[6]
                
            session['all_total_quantity'] = all_total_quantity #creates the total quantity and price sessions
            session['all_total_price'] = all_total_price
            
            return redirect(url_for('.book'))
        else:
            return 'Error while adding item to cart'
    except Exception as e:
        print(e)
    finally:
        cur.close()
        con.close()

@app.route('/empty')#when the user hits the empty button all the cart sessions are popped and made empty
@login_required
def empty_cart():
    session.pop('cart_item')
    session.pop('all_total_price',None)
    session.pop('all_total_quantity',None)
    return redirect(url_for('.book'))


@app.route('/delete/<string:ISBN>') #deletes the item from the cart
@login_required
def delete_product(ISBN):
    all_total_price = 0
    all_total_quantity = 0
    session.modified = True
    
    for item in session['cart_item'].items():
        if item[0] == ISBN:				
            session['cart_item'].pop(item[0], None)
            if 'cart_item' in session:
                for key, value in session['cart_item'].items():
                    individual_quantity = int(session['cart_item'][key]['quant'])
                    individual_price = float(session['cart_item'][key]['total_price'])
                    all_total_quantity = all_total_quantity + individual_quantity
                    all_total_price = all_total_price + individual_price
            break
    
    if all_total_quantity == 0:
        session.pop('cart_item',None)
        session.pop('all_total_price',None)
        session.pop('all_total_quantity',None)

    else:
        session['all_total_quantity'] = all_total_quantity
        session['all_total_price'] = all_total_price
    return redirect(url_for('.book'))
#TAKEN FROM WEEK 5 5001CEM
def array_merge( first_array , second_array ): #adds the lists together
	if isinstance( first_array , list ) and isinstance( second_array , list ):
		return first_array + second_array
	elif isinstance( first_array , dict ) and isinstance( second_array , dict ):#if its a dictionary, turns into a list then merges
		return dict( list( first_array.items() ) + list( second_array.items() ) )
	elif isinstance( first_array , set ) and isinstance( second_array , set ):
		return first_array.union( second_array )
	return False	

@app.route('/checkout') #this will checkout the cart
@login_required
def checkout():
    quantityError = "No books sir" #we create the quantity error session to use later
    session['quantityError'] = quantityError
    for key, value in session['cart_item'].items(): #we loop through all the items in the session
        quantity = int(session['cart_item'][key]['quant'])#we pull the quantity and the book name
        bookName = str(session['cart_item'][key]['bookName'])
        if 'quantityError' in session:
            session.pop('quantityError', None) #we empty the quantError session
        con = sqlite3.connect('mydatabase.db')
        cur = con.cursor();
        cur.execute("SELECT quant FROM books WHERE bookName=?;", [bookName]) # we pull the quant where it matches the book name
        curQuant= cur.fetchone()
        curQuant=str(curQuant).replace("(","")
        curQuant=str(curQuant).replace(")","")
        curQuant=str(curQuant).replace("'","")
        curQuant=str(curQuant).replace(",","")
        if int(curQuant) >= quantity: #if the quantity in the cart is less than the table this runs
            newQuant = int(curQuant) - quantity #calculate new quant
            con = sqlite3.connect('mydatabase.db')
            cur = con.cursor();
            update = "UPDATE books SET quant=" + str(newQuant) +" WHERE bookName ='" + bookName + "'" #update quant
            cur.execute(update)
            con.commit()
        elif int(curQuant) < quantity: #if the cart quantity is more than the table
            session['quantityError'] = quantityError # create session again
            session['cart_item'][key]['quant'] = int(curQuant)
            newQuant = 0
            con = sqlite3.connect('mydatabase.db')
            cur = con.cursor();
            update = "UPDATE books SET quant=" + str(newQuant) +" WHERE bookName ='" + bookName + "'" #quantity in table becomes 0
            cur.execute(update)
            con.commit()
            quantValue = session['cart_item'][key]['total_price'] #we update the prices based on the actual quantity we have
            session['cart_item'][key]['total_price'] = session['cart_item'][key]['retPrice']*int(curQuant)
            session['all_total_price']  = session['all_total_price'] - quantValue + (session['cart_item'][key]['retPrice']*int(curQuant))

    return render_template('checkout.html')



@app.route('/paynow', methods=['GET', 'POST'])
@login_required
def paynow():
    if request.method == 'POST': #this will load the pay now screen
        return clear_paynow(request.form['accountNum'],request.form['pinNum'])
    else:
        return show_paynow()
def show_paynow():
    return render_template('paynow.html',page=url_for('paynow'))

def clear_paynow(a,p): #empties all the sessions after paying
    session.pop('cart_item',None)
    session.pop('all_total_price',None)
    session.pop('all_total_quantity',None)
    return redirect(url_for('.book'))
    
