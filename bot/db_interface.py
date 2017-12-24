# *-* coding: utf-8 *-*

import pymysql
from settings import DB_HOST, DB_NAME, DB_USER, DB_PASSWORD


connection = pymysql.connect(host=DB_HOST,
                             user=DB_USER,
                             password=DB_PASSWORD,
                             db=DB_NAME,
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)


def reg_user(args_dic):
    with connection.cursor() as cursor:
        sql = 'insert into users(name, sex, weight, height) values (%s, %s, %s, %s)'
        cursor.execute(sql, (args_dic['name'], args_dic['sex'], args_dic['weight'], args_dic['height']))
    connection.commit()


def set_usernorm(username, daily_norm_dic):
    with connection.cursor() as cursor:
        sql = 'insert into norm(calories, proteins, fats, carbohydrates, user_id) values (%s, %s, %s, %s, (select id from users where name=%s))'
        cursor.execute(sql, (daily_norm_dic['calories'], daily_norm_dic['proteins'], daily_norm_dic['fats'], daily_norm_dic['carbohydrates'], username))
    connection.commit()


def get_daily_report(username):
    with connection.cursor() as cursor:
        sql = 'select calories, proteins, fats, carbohydrates from users where name=%s'
        cursor.execute(sql, username)
        return cursor.fetchall()


def get_daily_norm(username):
    with connection.cursor() as cursor:
        sql = 'select calories, proteins, fats, carbohydrates from norm where user_id=(select id from users where name=%s)'
        cursor.execute(sql, username)
        return cursor.fetchone()


def add_new_dish(title, description):
    with connection.cursor() as cursor:
        sql = 'insert into dishes(name, description) values (%s, %s)'
        cursor.execute(sql, (title, description))
    connection.commit()


def get_ingredients_types():
    with connection.cursor() as cursor:
        sql = 'select distinct type from ingredients;'
        cursor.execute(sql)
        return [i['type'] for i in cursor.fetchall()]


def get_inrgediets_by_type(type):
    with connection.cursor() as cursor:
        sql = 'select name from ingredients where type=%s'
        cursor.execute(sql, type)
        return [i['name'] for i in cursor.fetchall()]


def add_di(dish, ingredient, count):
    with connection.cursor() as cursor:
        sql = 'insert into d_i(dishes_id, ingredients_id, amount) values ((select id from dishes where name=%s), (select id from ingredients where name=%s), %s)'
        cursor.execute(sql, (dish, ingredient, count))
    connection.commit()


def is_dish_exist(dishname):
    with connection.cursor() as cursor:
        sql = 'select count(*) from dishes where name=%s'
        cursor.execute(sql, dishname)
        return cursor.fetchone()['count(*)'] != 0

def calc_dish_features(dishname):
    with connection.cursor() as cursor:
        sql = 'select sum(i.calories*di.amount/100) as calories, sum(i.proteins*di.amount/100) as proteins, \
        sum(i.fats*di.amount/100) as fats , sum(i.carbohydrates*di.amount/100) as carbohydrates from ingredients  as i join d_i as di join dishes as d on  \
        i.id=di.ingredients_id and d.id=di.dishes_id where d.name=%s'
        cursor.execute(sql, dishname)
        return cursor.fetchall()[0]

def get_curr_user_features(username):
    with connection.cursor() as cursor:
        sql = 'select calories, proteins, fats, carbohydrates from users where name=%s'
        cursor.execute(sql, username)
        return cursor.fetchall()[0]


def update_users_features(username, features):
    with connection.cursor() as cursor:
        sql = 'update users set calories=%s, proteins=%s, fats=%s, carbohydrates=%s where name=%s'
        cursor.execute(sql, (features['calories'], features['proteins'], features['fats'], features['carbohydrates'], username))
    connection.commit()

def delete_user(username):
    with connection.cursor() as cursor:
        sql = 'delete from users where name=%s'
        cursor.execute(sql, username)
    connection.commit()

