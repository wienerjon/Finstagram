#Import Flask Library
from flask import Flask, render_template, request, session, url_for, redirect
import pymysql.cursors
import datetime
import hashlib


def computeMD5hash(string):
    m = hashlib.md5()
    m.update(string.encode('utf-8'))
    return m.hexdigest()

#Initialize the app from Flask
app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

#Configure MySQL
conn = pymysql.connect(host='localhost',
                       port = 8889,
                       user='root',
                       password='root',
                       db='finstagram',
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

#Define a route to hello function
@app.route('/')
def hello():
    return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
    return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/home')
def home():

    user = session['username']
    cursor = conn.cursor();


    query = 'SELECT  photoID, photoPoster FROM Photo WHERE photoPoster = %s OR (photoID, photoPoster) IN(SELECT photoID, photoPoster FROM (Photo AS P JOIN Follow AS F ON (F.username_followed=P.photoPoster)) WHERE followstatus=TRUE AND P.allFollowers=True AND F.username_follower = %s)OR (photoID, photoPoster) IN (SELECT photoID, photoPoster FROM SharedWith JOIN BelongTo ON (SharedWith.groupOwner= BelongTo.owner_username AND SharedWith.groupName=BelongTo.groupName) WHERE SharedWith.photoID = photoID AND BelongTo.member_username = %s )order by postingDate DESC'
    
    cursor.execute(query, (user, user, user))
    data = cursor.fetchall()
    cursor.close()
    return render_template('home.html', username=user, posts=data)


@app.route('/post', methods=['GET', 'POST'])
def post():
    username = session['username']
    cursor = conn.cursor();

    filepath = request.form['filepath']
    caption = request.form['caption']
    isAllFollowers = request.form['isAllFollowers']
    if (isAllFollowers == 'true'):
        isAllFollowers = True
    else:
        isAllFollowers = False

    query = 'INSERT INTO photo (filepath, caption, allFollowers, photoPoster, postingdate) VALUES(%s, %s, %s, %s, %s)'
    cursor.execute(query, (filepath, caption, isAllFollowers, username, datetime.datetime.now()))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))




@app.route('/show_photo/<int:currPhotoID>', methods=["GET"])
def show_photo(currPhotoID):
    cursor = conn.cursor()
    user = session['username']

    query = 'SELECT * FROM photo JOIN Person ON(username=photoPoster)  WHERE photoID=%s'
    cursor.execute(query, (currPhotoID))
    data = cursor.fetchone()

    query = 'SELECT * FROM Tagged NATURAL JOIN Person WHERE photoID=%s AND tagstatus=TRUE'
    cursor.execute(query, (currPhotoID))
    taggees = cursor.fetchall()

    query = 'SELECT DISTINCT username, rating FROM Likes NATURAL JOIN Person WHERE photoID=%s'
    cursor.execute(query, (currPhotoID))
    likes = cursor.fetchall()

    query = 'SELECT * FROM photo JOIN Person ON(username=photoPoster)  WHERE photoID=%s AND username=%s'
    cursor.execute(query, (currPhotoID, user))
    owner = cursor.fetchone()

    query = 'SELECT * FROM Likes WHERE photoID=%s AND username=%s'
    cursor.execute(query, (currPhotoID, user))
    liked = cursor.fetchone()

    cursor.close()
    return render_template('show_photo.html', post=data, tagged=taggees, likees=likes, owner=owner, is_liked=liked)


@app.route('/like/<int:currPhotoID>', methods=['GET', 'POST'])
def like(currPhotoID):
    username = session['username']
    cursor = conn.cursor();
    rating = request.form['rating']

    query = 'INSERT INTO Likes (username, photoID, liketime, rating) VALUES(%s, %s, %s, %s)'
    cursor.execute(query, (username, currPhotoID, datetime.datetime.now(), rating))
    conn.commit()
    cursor.close()
    return show_photo(currPhotoID)

@app.route('/unlike/<int:currPhotoID>', methods=['GET', 'POST'])
def unlike(currPhotoID):
    user = session['username']
    cursor = conn.cursor();
    query = 'DELETE FROM Likes WHERE username = %s AND photoID = %s'
    cursor.execute(query, (user, currPhotoID))
    conn.commit()
    cursor.close()
    return show_photo(currPhotoID)

@app.route('/edit/<int:currPhotoID>', methods=['GET', 'POST'])
def edit(currPhotoID):
    cursor = conn.cursor();
    filepath = request.form['filepath']
    caption = request.form['caption']
    isAllFollowers = request.form['isAllFollowers']
    if (isAllFollowers == 'true'):
        isAllFollowers = True
        # delete sharedWith
        query = 'DELETE FROM SharedWith WHERE photoID = %s'
        cursor.execute(query, (currPhotoID))
        conn.commit()
    else:
        isAllFollowers = False        

    query = 'UPDATE Photo SET filepath=%s, caption=%s, allFollowers=%s WHERE photoID=%s'
    cursor.execute(query, (filepath, caption, isAllFollowers, currPhotoID))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))



@app.route('/edit_post/<int:currPhotoID>')
def edit_post(currPhotoID):
    cursor = conn.cursor()
    query = 'SELECT * FROM Photo WHERE photoID=%s'
    cursor.execute(query, (currPhotoID))
    data = cursor.fetchone()
    return render_template('edit_post.html', post=data)



@app.route('/delete_post/<int:currPhotoID>', methods=['GET', 'POST'])
def delete_post(currPhotoID):
    cursor = conn.cursor();
    # delete likes
    query = 'DELETE FROM Likes WHERE photoID = %s'
    cursor.execute(query, (currPhotoID))
    conn.commit()
    # delete tags
    query = 'DELETE FROM Tagged WHERE photoID = %s'
    cursor.execute(query, (currPhotoID))
    conn.commit()
    # delete sharedWith
    query = 'DELETE FROM SharedWith WHERE photoID = %s'
    cursor.execute(query, (currPhotoID))
    conn.commit()
    # delete photo
    query = 'DELETE FROM Photo WHERE photoID = %s'
    cursor.execute(query, (currPhotoID))
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))

@app.route('/follow', methods = ['GET','POST'])
def follow():
    username = session['username']
    cursor = conn.cursor();

    followed = request.form['followed']
    query = 'SELECT * FROM Person where username =%s'
    cursor.execute(query, (followed))   
    data = cursor.fetchone()

    # Put in a wrong username that doesnt exist
    error = None
    if(data is None):
        error = "Invalid Username"
        return render_template('search_to_follow.html', error=error)

    # check to see if the person they want to follow is themselves
    if(followed.lower() == username.lower()):
        error = 'Invlaid Follow Request'
        return render_template('search_to_follow.html', error=error)
    query = 'SELECT * FROM Follow WHERE username_followed=%s AND username_follower =%s'
    cursor.execute(query, (followed,username))
    data = cursor.fetchone()

    # the follow request already exists 
    if(data):
        error = 'Invalid Follow Request'
        return render_template('search_to_follow.html', error=error)


    query = 'INSERT INTO Follow (username_followed,username_follower, followstatus) VALUES(%s, %s, %s)'
    cursor.execute(query, (followed,username,False))
     
    conn.commit()
    cursor.close()
    return redirect(url_for('home'))
   


@app.route('/search_to_follow')
def search_to_follow():
    return render_template('search_to_follow.html')



@app.route('/manage_follow_requests')
def manage_follow_requests():
    user = session['username']
    cursor = conn.cursor();
    query = 'SELECT * FROM Follow WHERE username_followed = %s AND followstatus=FALSE'
    cursor.execute(query, (user))
    data = cursor.fetchall()
    cursor.close()
    return render_template('manage_follow_requests.html', pending=data)

@app.route('/accept_follower/<string:follower>', methods = ['GET', 'POST'])
def accept_follower(follower):
    user = session['username']
    cursor = conn.cursor();
    query = 'UPDATE Follow SET followstatus = TRUE WHERE username_followed = %s AND username_follower = %s'
    cursor.execute(query, (user, follower))
    conn.commit()
    cursor.close()
    return manage_follow_requests()

@app.route('/reject_follower/<string:follower>', methods = ['GET', 'POST'])
def reject_follower(follower):
    user = session['username']
    cursor = conn.cursor();
    query = 'DELETE FROM Follow WHERE username_followed = %s AND username_follower = %s'
    cursor.execute(query, (user, follower))
    conn.commit()
    cursor.close()

    return manage_follow_requests()


@app.route('/search_by_poster')
def search_by_poster():
    return render_template('search_by_poster.html', username = None, posts=None, error=None)

@app.route('/friendGroup')
def friendGroup():
    return render_template('friendGroup.html')

@app.route('/create_friendGroup', methods = ['GET','POST'])
def create_friendGroup():
    user = session['username']
    cursor = conn.cursor()
    group_name = request.form['group_name']
    description = request.form['description']
    query = 'SELECT * FROM Friendgroup WHERE groupOwner=%s AND groupName=%s'
    cursor.execute(query, (user,group_name))
    data = cursor.fetchone()
    error = None
    if (data):
        error = 'This group name is already used'
        return render_template('friendGroup.html', create_error=error)
    query = 'INSERT INTO Friendgroup (groupOwner, groupName, description) VALUES (%s, %s, %s)'
    cursor.execute(query, (user,group_name, description))
    query = 'INSERT INTO BelongTo (member_username, owner_username, groupName) VALUES (%s, %s, %s)'
    cursor.execute(query, (user,user,group_name))
    conn.commit()
    cursor.close()
    return render_template('friendGroup.html')

@app.route('/add_member', methods = ['GET','POST'])
def add_member():
    user = session['username']
    cursor = conn.cursor()
    group_name = request.form['group_name']
    member_name = request.form['member_name']
    query = 'SELECT * FROM Person WHERE username=%s'
    cursor.execute(query, (member_name))
    data = cursor.fetchone()
    error = None
    if (data is None):
        error = 'This member does not exist'
        return render_template('friendGroup.html', add_member_error=error)

    query = 'SELECT * FROM Friendgroup WHERE groupOwner=%s AND groupName=%s '
    cursor.execute(query, (user,group_name))
    data = cursor.fetchone()
    if (data is None):
        error = 'This group does not exist'
        return render_template('friendGroup.html', add_member_error=error)

    query = 'SELECT * FROM BelongTo WHERE owner_username=%s AND groupName=%s AND member_username=%s'
    cursor.execute(query, (user,group_name,member_name))
    data = cursor.fetchone()
    if (data):
        error = 'This member is already added'
        return render_template('friendGroup.html', add_member_error=error)
    query = 'INSERT INTO BelongTo (member_username, owner_username, groupName) VALUES (%s, %s, %s)'
    cursor.execute(query, (member_name,user,group_name))
    conn.commit()
    cursor.close()
    return render_template('friendGroup.html')

@app.route('/manage_share_post/<int:currPhotoID>', methods = ['GET','POST'])
def manage_share_post(currPhotoID, error=None):
    user = session['username']
    cursor = conn.cursor()
    query = 'SELECT * FROM BelongTo WHERE member_username=%s'
    cursor.execute(query, (user))
    groups = cursor.fetchall()
    cursor.close()
    return render_template('manage_share_post.html', photoID=currPhotoID, groups=groups, error=error)

@app.route('/share_to_friendGroup/<int:currPhotoID>', methods = ['GET','POST'])
def share_to_friendGroup(currPhotoID):
    group = request.form['group']
    group = group.split('|^|')
    cursor = conn.cursor()
    query = 'SELECT * FROM SharedWith WHERE groupOwner=%s AND groupName=%s AND photoID=%s'
    cursor.execute(query, (group[1],group[0],currPhotoID))
    # cursor.execute(query, (group.owner_username,group.groupName,currPhotoID))
    data = cursor.fetchone()
    error = None
    if (data):
        error = 'This photo is already shared with this group'
        return manage_share_post(currPhotoID, error)

    query = 'INSERT INTO SharedWith (groupOwner, groupName, photoID) VALUES (%s, %s, %s)'
    cursor.execute(query, (group[1],group[0],currPhotoID))
    conn.commit()
    cursor.close()
    return show_photo(currPhotoID)

@app.route('/search', methods = ['GET','POST'])
def search():
    user = session['username']
    cursor = conn.cursor()
    photoPoster = request.form['photoPoster']

    query = 'SELECT  photoID, photoPoster FROM Photo WHERE photoPoster = %s order by postingDate DESC '
    cursor.execute(query, (photoPoster))
    data = cursor.fetchall()
    
    error = None
    if(len(data)==0):
        error = "Invalid Username"
        cursor.close()
        return render_template('search_by_poster.html', error=error)
    query = 'SELECT * FROM Follow where username_followed = %s and username_follower =%s and followStatus= 1'
    cursor.execute(query, (photoPoster,user))
    isFollowed = cursor.fetchall()

    if(len(isFollowed)==0):
        error = "You are not following this person"
        cursor.close()
        return render_template('search_by_poster.html', error=error)


    cursor.close()
    return render_template('search_by_poster.html', username = photoPoster, posts=data, error=error)


@app.route('/analytics', methods=['GET', 'POST'])
def analytics():
    user = session['username']
    cursor = conn.cursor()
    # total number of posts
    query = 'SELECT COUNT(photoID) AS num_photos FROM Photo WHERE photoPoster=%s'
    cursor.execute(query, (user))
    num_photos = cursor.fetchone()["num_photos"]
    # total number of followers
    query = 'SELECT COUNT(username_follower) AS num_followers FROM Follow WHERE username_followed=%s'
    cursor.execute(query, (user))
    num_followers = cursor.fetchone()["num_followers"]
    # total number followering
    query = 'SELECT COUNT(username_followed) AS num_following FROM Follow WHERE username_follower=%s'
    cursor.execute(query, (user))
    num_following = cursor.fetchone()["num_following"]
    #this is a query to find all the pictures with all the likes it has.
    query = 'SELECT photoID, photoPoster, SUM(rating) AS total_rating FROM photo NATURAL JOIN likes WHERE photoPoster= %s group by photoPoster, photoID'
    cursor.execute(query, (user))
    total_likes = cursor.fetchall()
    
    # this query is to find the picture/s that has/have the most likes
    query = 'SELECT photoID, photoPoster, SUM(rating) AS total_rating FROM photo NATURAL JOIN likes GROUP BY photoPoster, photoID HAVING SUM(rating)=(SELECT MAX(max_value) FROM (SELECT SUM(rating) AS max_value FROM photo NATURAL JOIN likes WHERE photoPoster= %s group by photoPoster, photoID) AS T)'
    cursor.execute(query, (user))
    most_liked = cursor.fetchall()
    cursor.close()
    return render_template('analytics.html', total_likes=total_likes, user=user, most_liked=most_liked, num_followers=num_followers, num_following=num_following, num_photos=num_photos)










#Authenticates the login
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password']

    #cursor used to send queries
    cursor = conn.cursor()
    
    password_hashed = computeMD5hash(password)
    query = 'UPDATE Person SET password = %s where username= %s'
    cursor.execute(query,(password_hashed, username))
    conn.commit()

    #executes query
    query = 'SELECT * FROM Person WHERE username = %s and password = %s'
    cursor.execute(query, (username, password_hashed))
    
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row

       
    cursor.close()
    
    error = None
    if(data):
        #creates a session for the the user
        #session is a built in
        session['username'] = username
       
        return redirect(url_for('home'))


    else:
        #returns an error message to the html page
        error = 'Invalid login or username'
        return render_template('login.html', error=error)


#Authenticates the register
@app.route('/registerAuth', methods=['GET', 'POST'])
def registerAuth():
    #grabs information from the forms
    username = request.form['username']
    password = request.form['password']
    firstName = request.form['firstName']
    lastName = request.form['lastName']
    bio = request.form['bio']

    password = computeMD5hash(password)
    #cursor used to send queries
    cursor = conn.cursor()
    #executes query
    query = 'SELECT * FROM Person WHERE username = %s'
    cursor.execute(query, (username))
    #stores the results in a variable
    data = cursor.fetchone()
    #use fetchall() if you are expecting more than 1 data row
    error = None
    if(data):
        #If the previous query returns data, then user exists
        error = "This user already exists"
        return render_template('register.html', error = error)
    else:
        ins = 'INSERT INTO Person VALUES(%s, %s, %s, %s, %s)'
        cursor.execute(ins, (username, password, firstName, lastName, bio))
        conn.commit()
        cursor.close()
        return render_template('index.html')

        
@app.route('/logout')
def logout():
    session.pop('username')
    return redirect('/')




# @app.route('/select_blogger')
# def select_blogger():
#     #check that user is logged in
#     #username = session['username']
#     #should throw exception if username not found
    
#     cursor = conn.cursor();
#     query = 'SELECT DISTINCT username FROM blog'
#     cursor.execute(query)
#     data = cursor.fetchall()
#     cursor.close()
#     return render_template('select_blogger.html', user_list=data)

# @app.route('/show_posts', methods=["GET", "POST"])
# def show_posts():
#     poster = request.args['poster']
#     cursor = conn.cursor();
#     query = 'SELECT ts, blog_post FROM blog WHERE username = %s ORDER BY ts DESC'
#     cursor.execute(query, poster)
#     data = cursor.fetchall()
#     cursor.close()
#     return render_template('show_posts.html', poster_name=poster, posts=data)

        
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
    app.run('127.0.0.1', 5000, debug = True)
