CREATE TABLE user_plans (
    telegram_id BIGINT PRIMARY KEY,
    plan TEXT NOT NULL
);

CREATE TABLE subscriptions (
    telegram_id BIGINT PRIMARY KEY,
    plan TEXT NOT NULL,
    price INT NOT NULL,
    duration INT NOT NULL
);