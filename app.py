from flask import Flask, flash, Blueprint, render_template, request, redirect, session, current_app, url_for
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
from os import path
import os
from datetime import datetime, timedelta
from generate_weaks import generate_weeks

# Создание приложения Flask
app = Flask(__name__)

# Конфигурация приложения
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'другой-секретный-секрет')
app.config['DB_TYPE'] = os.getenv('DB_TYPE', 'postgres')
def db_connect():
    if current_app.config['DB_TYPE'] == 'postgres':
        conn = psycopg2.connect(
            host='127.0.0.1',
            database='antonov_rgr',
            user='antonov_rgr',
            password='123'
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        dir_path = path.dirname(path.realpath(__file__))
        db_path = path.join(dir_path, 'database.db')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    return conn, cur

def db_close(conn, cur):
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form.get('fullname')
        login = request.form.get('login')
        password = request.form.get('password')

        if not fullname or not login or not password:
            return 'Все поля обязательны для заполнения.', 400

        hashed_password = generate_password_hash(password)

        conn, cur = db_connect()
        try:
            cur.execute("SELECT * FROM users WHERE login = %s", (login,))
            existing_user = cur.fetchone()

            if existing_user:
                return 'Пользователь с таким логином уже существует.', 400

            cur.execute(
                "INSERT INTO users (fullname, login, password) VALUES (%s, %s, %s)",
                (fullname, login, hashed_password)
            )
        finally:
            db_close(conn, cur)

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')

        conn, cur = db_connect()
        try:
            cur.execute("SELECT * FROM users WHERE login = %s", (login,))
            user = cur.fetchone()

            if not user or not check_password_hash(user['password'], password):
                return 'Неверный логин или пароль.', 400

            session['user_id'] = user['id']
        finally:
            db_close(conn, cur)

        return redirect(url_for('main'))

    return render_template('login.html')



@app.route('/vacation', methods=['GET', 'POST'])
def vacation():
    year = request.args.get('year', datetime.now().year, type=int)
    user_id = session.get('user_id')

    conn, cur = db_connect()
    try:
        if request.method == 'POST':
            # Проверяем, если нажата кнопка "Отменить"
            unmark_week = request.form.get('unmark')
            if unmark_week:
                # Удаляем пометку об отпуске для текущего пользователя
                cur.execute(
                    "DELETE FROM vacation WHERE user_id = %s AND year = %s AND week_number = %s",
                    (user_id, year, unmark_week)
                )
                flash(f'Неделя {unmark_week} успешно отменена.', 'success')
                return redirect(url_for('vacation', year=year))

            # Обработка добавления новых недель
            selected_weeks = request.form.getlist('weeks')

            # Проверка, что пользователь выбрал не более 4 недель
            if len(selected_weeks) > 4:
                flash('Вы можете выбрать не более 4 недель.', 'danger')
                return redirect(url_for('vacation', year=year))

            # Проверка, что пользователь уже выбрал 4 недели в этом году
            cur.execute("SELECT COUNT(*) FROM vacation WHERE user_id = %s AND year = %s", (user_id, year))
            current_count = cur.fetchone()['count']

            if current_count + len(selected_weeks) > 4:
                flash('Вы уже выбрали 4 недели отпуска в этом году.', 'danger')
                return redirect(url_for('vacation', year=year))

            # Проверка занятых недель
            for week in selected_weeks:
                cur.execute("SELECT * FROM vacation WHERE year = %s AND week_number = %s", (year, week))
                existing = cur.fetchone()
                if existing and existing['user_id'] != user_id:
                    flash(f'Неделя {week} уже занята другим пользователем.', 'danger')
                    return redirect(url_for('vacation', year=year))

            # Добавление новых недель
            for week in selected_weeks:
                cur.execute(
                    "INSERT INTO vacation (user_id, year, week_number) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (user_id, year, week)
                )

            flash('Ваш отпуск успешно сохранён.', 'success')
            return redirect(url_for('vacation', year=year))

        # Получение данных о текущем отпуске с именами пользователей
        cur.execute("""
            SELECT vacation.week_number, vacation.user_id, users.fullname AS username
            FROM vacation
            LEFT JOIN users ON vacation.user_id = users.id
            WHERE vacation.year = %s
        """, (year,))
        occupied_weeks = cur.fetchall()

        # Генерация списка недель
        weeks = generate_weeks(year)
        for week in weeks:
            for occupied in occupied_weeks:
                if week['week_number'] == occupied['week_number']:
                    week['occupied'] = occupied['user_id']
                    week['username'] = occupied['username']

        return render_template('vacation.html', weeks=weeks, year=year)

    finally:
        db_close(conn, cur)


@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))