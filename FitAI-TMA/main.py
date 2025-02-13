from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import asyncpg
import os
import requests

app = FastAPI()

# CORS middleware для взаимодействия с Telegram Web App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Установим API-ключ OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Подключение к БД
DATABASE_URL = os.getenv("DATABASE_URL")

async def get_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

# Модель данных пользователя
class UserData(BaseModel):
    telegram_id: int
    age: int
    weight: float
    height: float
    goal: str  # "weight_loss", "muscle_gain", "tone"

@app.post("/generate_plan/")
async def generate_plan(user: UserData, db=Depends(get_db)):
    prompt = f"""
    Составь персональный план питания и тренировок для человека:
    - Возраст: {user.age} лет
    - Рост: {user.height} см
    - Вес: {user.weight} кг
    - Цель: {user.goal}
    """
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "Ты - фитнес-тренер и нутрициолог."},
                  {"role": "user", "content": prompt}]
    )
    plan = response["choices"][0]["message"]["content"]
    
    # Сохранение плана в БД
    await db.execute("""INSERT INTO user_plans (telegram_id, plan) VALUES ($1, $2)""", user.telegram_id, plan)
    return {"plan": plan}

# Авторизация через Telegram OAuth
@app.get("/auth/")
async def authenticate(telegram_id: int, first_name: str, auth_date: int, hash: str):
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    data_check_string = f"telegram_id={telegram_id}&first_name={first_name}&auth_date={auth_date}"
    
    # Проверка валидности подписи
    response = requests.get(f"https://api.telegram.org/bot{telegram_bot_token}/getMe")
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Invalid Telegram authentication")
    
    return {"message": "Authentication successful", "telegram_id": telegram_id}

# Опции подписки
SUBSCRIPTION_PLANS = {
    "monthly": {"price": 10, "duration": 30},
    "quarterly": {"price": 24, "duration": 90},
    "semiannual": {"price": 42, "duration": 180},
    "annual": {"price": 72, "duration": 365}
}

@app.post("/subscribe/")
async def subscribe(telegram_id: int, plan: str, db=Depends(get_db)):
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="Invalid subscription plan")
    
    subscription = SUBSCRIPTION_PLANS[plan]
    
    # Запись подписки в БД
    await db.execute("""INSERT INTO subscriptions (telegram_id, plan, price, duration) VALUES ($1, $2, $3, $4)""", telegram_id, plan, subscription["price"], subscription["duration"])
    
    return {"message": "Subscription successful", "plan": plan, "price": subscription["price"]}