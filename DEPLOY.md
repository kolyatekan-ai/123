# Как сделать сайт доступным для друзей

## Вариант 1: Бесплатный хостинг (Render.com) - РЕКОМЕНДУЮ

1. Зарегистрируйтесь на https://render.com (через GitHub)
2. Создайте новый "Web Service"
3. Подключите GitHub репозиторий с этим кодом
4. Настройки:
   - Build Command: `npm install`
   - Start Command: `npm start`
5. Нажмите "Create Web Service"
6. Через 2-3 минуты сайт будет доступен по адресу типа `https://your-app.onrender.com`

## Вариант 2: Быстро через GitHub + Render

```bash
cd C:\123\voice-chat
git init
git add .
git commit -m "Initial commit"
```

Затем создайте репозиторий на GitHub и выполните:
```bash
git remote add origin https://github.com/ваш-логин/voice-chat.git
git push -u origin main
```

После этого подключите репозиторий к Render.com

## Вариант 3: Временно через ngrok (только для теста)

```bash
# Установите ngrok: https://ngrok.com/download
ngrok http 3000
```

Скопируйте ссылку вида `https://xxxx.ngrok.io` и отправьте друзьям.

## Важно для WebRTC

Для работы голосового чата через интернет нужен HTTPS. Все современные браузеры требуют HTTPS для доступа к микрофону на публичных сайтах.

При деплое на Render.com HTTPS настраивается автоматически.
