import os
from os import environ
from os.path import join, dirname
from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING
import jwt
from datetime import datetime, timedelta
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename
from flask import request, redirect, url_for
from bson import ObjectId, json_util
from flask import abort

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

client = MongoClient(
    environ.get('MONGODB_URL'))

db = client.mebest

SECRET_KEY = environ.get('SECRET_KEY')

TOKEN_KEY = environ.get('TOKEN_KEY')

app = Flask(__name__)


@app.route('/')
def index():
    # Ambil 4 data terbaru dari koleksi tours
    token_receive = request.cookies.get(TOKEN_KEY)
    tours_data = db.tours.find().limit(4).sort('_id', -1)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        data_user = db.users.find_one(
            {'username': payload['id'], 'role': payload['role']})
        return render_template('index.html', tours_data=tours_data, payloads=data_user, token_key=TOKEN_KEY)

    except jwt.ExpiredSignatureError:
        return redirect(url_for('to_login', msg="Session berakhir,Silahkan Login Kembali"))
    except jwt.exceptions.DecodeError:
        return render_template('index.html', tours_data=tours_data)


@app.route('/tours')
def tours():
    tours_search = request.args.get('filtered_tours')
    tours_data = []  # You need to populate this with actual data from your database
    token_receive = request.cookies.get(TOKEN_KEY)
    tours_data = db.tours.find()
    result = request.args.get('result', '')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        data_user = db.users.find_one(
            {'username': payload['id'], 'role': payload['role']})
        if tours_search:
            return render_template('tours.html', tours_data=json_util.loads(tours_search), result=result, payloads=data_user, token_key=TOKEN_KEY,)
        return render_template('tours.html', tours_data=tours_data, payloads=data_user, token_key=TOKEN_KEY, result=result)

    except jwt.ExpiredSignatureError:
        return redirect(url_for('to_login', msg="Session berakhir,Silahkan Login Kembali"))
    except jwt.exceptions.DecodeError:
        if tours_search:
            return render_template('tours.html', tours_data=json_util.loads(tours_search), result=result)
        return render_template('tours.html', tours_data=tours_data, result=result)


@app.route('/documentation')
def documentation():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        data_user = db.users.find_one(
            {'username': payload['id'], 'role': payload['role']})
        return render_template('documentation.html', payloads=data_user, token_key=TOKEN_KEY)

    except jwt.ExpiredSignatureError:
        return redirect(url_for('to_login', msg="Session berakhir,Silahkan Login Kembali"))
    except jwt.exceptions.DecodeError:
        return render_template('documentation.html')


@app.route('/cek_pesanan')
def cek_pesanan():
    try:
        token_receive = request.cookies.get(TOKEN_KEY)
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        data_user = db.users.find_one(
            {'username': payload['id'], 'role': payload['role']})
        if payload['role'] == 1:
            orders = db.orders.find().sort('order_date', DESCENDING)
            orders_data = []
            for order in orders:
                tour_data = db.tours.find_one({'_id': order['tour_id']})
                order['tour'] = tour_data['title']
                order['image'] = tour_data['image_path']
                order['order_date'] = order['order_date'].strftime(
                    "%Y-%m-%d %H:%M:%S")
                orders_data.append(order)
            pass
        elif payload['role'] == 2:
            orders = db.orders.find({'user_id': ObjectId(payload['_id'])}).sort(
                'order_date', DESCENDING)
            orders_data = []
            for order in orders:
                tour_data = db.tours.find_one({'_id': order['tour_id']})
                order['tour'] = tour_data['title']
                order['image'] = tour_data['image_path']
                order['order_date'] = order['order_date'].strftime(
                    "%Y-%m-%d %H:%M:%S")
                orders_data.append(order)

        return render_template('cekPesanan.html', payloads=data_user, orders_data=orders_data, token_key=TOKEN_KEY)

    except jwt.ExpiredSignatureError:
        return redirect(url_for('to_login', msg="Session berakhir,Silahkan Login Kembali"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for('to_login', msg="Anda Belum Login"))


@app.route('/update_pesanan', methods=['POST'])
def update_pesanan():
    try:
        status = request.form['status']
        order_id = request.form['order_id']
        order_object_id = ObjectId(order_id)

        updated_order = db.orders.find_one_and_update(
            {'_id': order_object_id}, {'$set': {'status': status}})

        if updated_order:
            return jsonify({'result': 'success', 'msg': 'Pesanan berhasil dihapus'})
        else:
            return jsonify({'result': 'failed', 'msg': 'Pesanan tidak ditemukan'})
    except Exception as e:
        return jsonify({'result': 'failed', 'msg': str(e)})


@app.route('/about')
def about():
    token_receive = request.cookies.get(TOKEN_KEY)
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        data_user = db.users.find_one(
            {'username': payload['id'], 'role': payload['role']})
        return render_template('about.html', payloads=data_user, token_key=TOKEN_KEY)

    except jwt.ExpiredSignatureError:
        return redirect(url_for('to_login', msg="Session berakhir,Silahkan Login Kembali"))
    except jwt.exceptions.DecodeError:
        return render_template('about.html')

# authentikasi


@app.route("/to_register", methods=['GET'])
def to_register():
    return render_template('register.html')


@app.route("/to_login", methods=['GET'])
def to_login():
    msg = request.args.get('msg')
    return render_template('login.html', msg=msg)


@app.route('/login', methods=['POST'])
def login():
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    password_hash = hashlib.sha256(
        (password_receive).encode('utf-8')).hexdigest()
    print(username_receive, password_hash)
    result = db.users.find_one({
        'username': username_receive,
        'password': password_hash
    })
    if (result):
        payload = {
            'id': result['username'],
            '_id': str(result['_id']),
            'role': result['role'],
            'exp': datetime.utcnow() + timedelta(seconds=60*60)
        }
        print(payload['exp'])
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return jsonify({
            'result': 'success',
            'token': token,
            'token_key': TOKEN_KEY,
        })
    else:
        return jsonify({
            'result': 'failed',
            'msg': 'username dan password tidak ditemukan di database'
        })


@app.route('/register', methods=['POST'])
def register():
    nickname_receive = request.form['nickname_give']
    username_receive = request.form['username_give']
    password_receive = request.form['password_give']
    print(nickname_receive)

    password_hash = hashlib.sha256(
        (password_receive).encode('utf-8')).hexdigest()
    cek_data_nama = db.users.find_one({'nickname': nickname_receive})
    cek_nama = bool(cek_data_nama)
    print(cek_nama)
    if (cek_nama == True):
        return jsonify({
            'result': 'failed_name',
            'msg': 'Nickname already exists!, please try input again'
        })

    doc = {
        'nickname': nickname_receive,
        'username': username_receive,
        'password': password_hash,
        'role': 2
    }

    db.users.insert_one(doc)

    return jsonify({
        'result': 'success',
        'msg': 'Successfully registered!'
    })

# end autentikasi


@app.route('/detail_tours')
def detail_tours():
    token_receive = request.cookies.get(TOKEN_KEY)
    tour_id = request.args.get('id')
    tour_details = db.tours.find_one({'_id': ObjectId(tour_id)})
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload['id'])
        print(payload['role'])
        db_user = db.users.find_one(
            {'username': payload['id'], 'role': payload['role']})
        print(db_user)
        return render_template('detail.html', tour_details=tour_details, payloads=db_user, token_key=TOKEN_KEY, db_user=db_user)

    except jwt.ExpiredSignatureError:
        return redirect(url_for('to_login', msg="Session berakhir,Silahkan Login Kembali"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for('to_login', msg="Anda Belum Login"))


UPLOAD_FOLDER = 'static/img'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Fungsi untuk memeriksa apakah ekstensi file diizinkan


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/add_tour', methods=['POST'])
def add_tour():
    if request.method == 'POST':
        tour_title = request.form['tourTitle']
        tour_description = request.form['tourDescription']
        tour_price = int(request.form['tourPrice'])
        print(tour_title, tour_description, tour_price)

        if 'tourImage' not in request.files:
            return jsonify({'result': 'failed', 'msg': 'Tidak ada bagian file'})

        file = request.files['tourImage']

        if file.filename == '':
            return jsonify({'result': 'failed', 'msg': 'Tidak ada file yang dipilih'})

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Memasukkan data ke dalam database
            db.tours.insert_one({
                'title': tour_title,
                'description': tour_description,
                'price': tour_price,
                'image_path': file_path
            })

            print('success')

            # Redirect to the tours page with success message as a query parameter
            return redirect(url_for('tours', result='success'))

    # Redirect to the tours page with failure message as a query parameter
    return redirect(url_for('tours', result='failed'))


@app.route('/get_tour_details', methods=['GET'])
def get_tour_details():
    tour_id = request.args.get('id')
    tour_details = db.tours.find_one({'_id': ObjectId(tour_id)})
    return jsonify({
        'title': tour_details['title'],
        'description': tour_details['description'],
        'price': tour_details['price']

    })


@app.route('/update_tour', methods=['POST'])
def update_tour():
    if request.method == 'POST':
        # Ambil data dari formulir
        tour_id = request.form['editTourId']
        new_title = request.form['editTourTitle']
        new_description = request.form['editTourDescription']
        new_price = float(request.form['editTourPrice'])
        new_image = request.files['editTourImage']

        tour_object_id = ObjectId(tour_id)

        db.tours.update_one(
            {'_id': tour_object_id},
            {
                '$set': {
                    'title': new_title,
                    'description': new_description,
                    'price': new_price,
                }
            }
        )

        if new_image:
            filename = secure_filename(new_image.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            new_image.save(file_path)

            db.tours.update_one(
                {'_id': tour_object_id},
                {
                    '$set': {
                        'image_path': file_path
                    }
                }
            )

        # Redirect ke halaman tours.html setelah berhasil memperbarui
        return redirect(url_for('tours'))

    return jsonify({'result': 'failed', 'msg': 'Permintaan tidak valid'})


@app.route('/delete_tour', methods=['POST'])
def delete_tour():
    if request.method == 'POST':
        try:
            tour_id = request.form['deleteTourId']

            # Gunakan ObjectId dari pymongo untuk mencocokkan _id di database
            tour_object_id = ObjectId(tour_id)

            # Hapus data tur dari database berdasarkan _id
            deleted_tour = db.tours.find_one_and_delete(
                {'_id': tour_object_id})

            if deleted_tour:
                return jsonify({'result': 'success', 'msg': 'Tur berhasil dihapus'})
            else:
                return jsonify({'result': 'failed', 'msg': 'Tur tidak ditemukan'})
        except Exception as e:
            return jsonify({'result': 'failed', 'msg': str(e)})

    return jsonify({'result': 'failed', 'msg': 'Permintaan tidak valid'})


@app.route('/booking', methods=['POST'])
def booking_tour():
    tour = ObjectId(request.form['tour'])
    nama = request.form['nama']
    no_telp = request.form['no_telp']
    jumlah_tiket = int(request.form['jumlah_tiket'])
    jenis_paket = request.form['jenis_paket']
    tanggal_tour = request.form['tanggal_tour']
    no_telp = request.form['no_telp']
    total_harga = request.form['total_harga']

    token_receive = request.cookies.get(TOKEN_KEY)
    payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
    user_id = ObjectId(payload['_id'])

    db.orders.insert_one({
        'nama': nama,
        'no_telp': no_telp,
        'jumlah_tiket': jumlah_tiket,
        'jenis_paket': jenis_paket,
        'tanggal_tour': tanggal_tour,
        'total_harga': total_harga,
        'status': 'pending',
        'tour_id': tour,
        'user_id': user_id,
        'order_date': datetime.now()
    })

    return redirect('cek_pesanan')


@app.route('/search_tours', methods=['POST'])
def search_tours():
    search_term = request.form.get('searchTerm', '').lower()
    tours_data = db.tours.find()
    filtered_tours = json_util.dumps([tour for tour in tours_data if search_term in tour['title'].lower(
    ) or search_term in tour['description'].lower()])
    print(filtered_tours)
    return jsonify({'filtered_tours': filtered_tours, 'result': 'success'})


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
