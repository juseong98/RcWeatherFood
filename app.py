# -*- coding: utf-8 -*-
"""
Created on Mon Aug 21 10:15:14 2023

@author: 407-16
"""

from flask import Flask, render_template, jsonify, request, redirect
from bs4 import BeautifulSoup
from pprint import pprint
import requests
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import pymysql
import json
import time
import threading


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# DB 음식정보 select ==================================================
def GetFood(result, foodnum = None, limit = None, orderby = None):
    
    db = 1  
    
    if db == 0 :
        db = pymysql.connect(host='127.0.0.1',
                             user='root',
                             password='ezen',
                             database='food',
                             cursorclass=pymysql.cursors.DictCursor)
    elif db == 1 :
        db = pymysql.connect(host='192.168.0.112',
                             user='ezen',
                             password='ezen',
                             database='food',
                             cursorclass=pymysql.cursors.DictCursor)
    run = db.cursor()
    
    # SQL query 작성
    sql  = "select * from food "
    sql += "where weather_menu = '" + result + "' "
    
    # 해당 음식 데이터만 select
    if foodnum != None :
        sql += "and foodnum = '" + foodnum + "' "
    
    # select 데이터 갯수 제한
    if limit != None :
        sql += "limit 0, " + limit
        
    # 데이터 정렬
    if orderby != None :
        sql += "order by " + orderby + " "
    
    # SQL query 실행
    run.execute(sql)
    
    # SQL query 실행 결과를 가져옴
    food = run.fetchall()
    db.close()
    return food

# 선택한 음식 기반으로 추천 ==================================================
def Recommend(weather, foodnum):
    # 선택한 음식 DB에서 select
    foodSelect = GetFood(weather, foodnum)
    
    # 날씨 음식 DB에서 select
    rc_food = GetFood(weather)
    rc_food = pd.DataFrame(rc_food)
    
    # 카운터 벡터라이즈 학습
    cv = CountVectorizer(ngram_range=(1,3)) 
    cv_category = cv.fit_transform(rc_food['food_category'])
    similarity_category = cosine_similarity(cv_category, cv_category).argsort()[:,::-1]
    
    def recommend_menu(df, menu_name):
        target_menu_idx = df[df['foodname'] == menu_name].index.values
    
        sim_idx = similarity_category[target_menu_idx].reshape(-1)
        sim_idx = sim_idx[sim_idx != target_menu_idx]
    
        result = df.iloc[sim_idx]
        return result
    
    recommend = recommend_menu(rc_food, foodSelect[0]['foodname']).head(10)
    recommend = recommend.to_json(orient='records')
    
    return recommend

# 메인 페이지 ( 크롤링 날씨 데이터, 날씨에 맞는 음식 ) =========================
@app.route('/', methods=['GET','POST'])
def GetData():

    return render_template('index.html')

# 위도, 경도를 반환 =============================================
@app.route('/location', methods=['GET','POST'])
def location():
    
    jsonData = request.get_json("jsonip")
    ip = jsonData['ip']
    
    # ipstack api
    key = '52c1edc6a6ce49175511d0a4a9bf8171'
    url = 'http://api.ipstack.com/' + ip + '?access_key=' + key + '&format=1'
    
    result = requests.get(url)
    result = json.loads(result.text)
    lat = str(result['latitude'])
    lon = str(result['longitude'])
    
    # openweather api
    key = 'a80651fc18ea43dd3f758b9ac20be1fa'
    url = 'https://api.openweathermap.org/data/2.5/weather?lat='+lat+'&lon='+lon+'&appid='+ key +'&units=metric&lang=kr'
    
    result = requests.get(url)
    result = json.loads(result.text)
    
    return jsonify(result)

# 메인 페이지 ajax ( 날씨 변경, 정렬 변경 ) =============================================
@app.route('/ajax', methods=['GET','POST'])
def ajax():
    # select에서 선택한 날씨로 갱신
    
    jsonData = request.get_json("data")
    todo = jsonData['todo'] # todo : weather ( 날씨 변경 ) / orderby ( 정렬 변경 )
    weatherSelect = jsonData['weatherSelect']
    data = GetFood(weatherSelect)
    
    if todo == "orderby" :
        orderby = jsonData['orderby']
        data = GetFood(weatherSelect, orderby = orderby)
    
    return jsonify(data)


# 결과 페이지 ( 선택한 음식에 맞는 추천 목록, 날씨에 맞는 추천 목록 ) =========================
@app.route('/result/<weather>/<foodnum>', methods=['GET','POST'])
def result(weather, foodnum):
    
    # 선택한 음식 정보 DB에서 select ( foodnum 잘못된 경우 index로 이동 )
    foodSelect = GetFood(weather, foodnum)
    try :
        foodSelect = foodSelect[0]
    except :    
        return redirect('/')
    
    # 추천 함수 
    foodRec = Recommend(weather, foodnum)
    
    # 날씨 음식 DB에서 select
    foodWeather = GetFood(weather, limit='5')
    
    return render_template('result.html',
                           foodnum = foodnum, 
                           weather = weather,
                           foodSelect = foodSelect,
                           foodRec = foodRec,
                           foodWeather = foodWeather)

# 404 에러 index로 이동 =======================================================
@app.errorhandler(404)
def page_not_found(error):
    return redirect('/')
@app.errorhandler(500)
def page_not_found1(error):
    return render_template('index.html'), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port="5000", debug=True, threaded=True)