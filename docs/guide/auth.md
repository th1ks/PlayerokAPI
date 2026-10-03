# Авторизация и профиль

## Готовый токен

Обычный путь — взять cookie `token` из браузера и отдать её клиенту:

```python
acc = Account(token=os.environ["PLAYEROK_TOKEN"])
```

Токен можно заменить на лету, например после перелогина:

```python
acc.token = новый_токен
```

Кэш профиля при этом сбрасывается.

## Вход по коду на почту

Если хочется получить токен из кода, площадка присылает одноразовый код
на e-mail.

```python
async with Account() as acc:
    await acc.auth.send_otp("mail@example.com")
    result = await acc.auth.confirm_otp("mail@example.com", "123456")

    if result.requires_two_factor:
        acc.token = await acc.auth.confirm_second_factor(result, "654321")

    print(acc.token)
```

{meth}`~PlayerokAPI.methods.auth.AuthMethods.confirm_otp` возвращает
{class}`~PlayerokAPI.methods.auth.OtpResult`. Если двухфакторная
аутентификация выключена, токен уже проставлен в клиент — второй шаг
не нужен.

`confirm_second_factor` принимает и результат целиком, и голый токен
сессии из `result.second_factor_token`.

:::{warning}
Код на почту приходит владельцу адреса. Не вызывайте `send_otp` для
чужих адресов.
:::

## Выход

```python
await acc.auth.logout()
```

Сессия на стороне площадки закрывается, токен в клиенте очищается.

## Профиль

```python
me = await acc.get_me()

me.username
me.role  # UserRole
me.balance.available  # доступно к трате
me.balance.frozen  # заморожено по активным сделкам
me.balance.pending_income  # придёт после подтверждения сделок
me.unread_chats_counter
me.testimonial_counter
me.rating
```

{meth}`~PlayerokAPI.Account.get_me` кэширует результат в `acc.id` —
идентификатор нужен, например, чтобы в чате отличить свои сообщения
от чужих.

Отдельно баланс:

```python
balance = await acc.get_balance()
```

## Настройки аккаунта

```python
await acc.viewer.config()  # настройки интерфейса
await acc.viewer.bindings()  # привязанные способы входа
await acc.viewer.notifications()  # состояние уведомлений
await acc.viewer.chosen_card()  # карта для выплат
```

## Имя пользователя

```python
if not await acc.viewer.is_username_taken("newnick"):
    await acc.viewer.register_username("newnick")
```

## Аватар

Файл сначала загружается в хранилище, потом привязывается к профилю:

```python
file_id = await acc.files.upload_path("avatar.png")
await acc.viewer.set_avatar(file_id)
```

## Двухфакторная аутентификация

Включение в три шага: код на почту, подтверждение кода, подтверждение
кодом из приложения-аутентификатора.

```python
await acc.viewer.request_two_factor_email_code()
response = await acc.viewer.verify_two_factor_email_code("123456")
await acc.viewer.confirm_two_factor(response["token"], "654321")
```

Проверить состояние и выключить:

```python
await acc.viewer.two_factor()
await acc.viewer.disable_two_factor()
```

## Уведомления

```python
from PlayerokAPI.enums import NotificationProviderId

for channel in await acc.notifications.channels():
    print(channel.id, channel.enabled)

await acc.notifications.enable(NotificationProviderId.TELEGRAM)
link = await acc.notifications.telegram_bot_link()
print("Подпишитесь на бота:", link)
```

{meth}`~PlayerokAPI.methods.notifications.NotificationsMethods.generate_telegram_bot_link`
выпускает новую ссылку — старая после этого перестаёт работать.
